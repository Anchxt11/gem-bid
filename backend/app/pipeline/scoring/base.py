from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


# ---------------------------------------------------------------------------
# Enums — mirror the Postgres native enums where they overlap (RequirementStatus
# maps to the DB's `status` column on compliance_results; RiskLevel maps to
# the DB's `RiskLevel` enum). MatchStatus mirrors Layer 3's Tier 3 LLM output
# contract from the handoff doc (match / minor_discrepancy / major_discrepancy
# / unverifiable) plus portal_unavailable, which Layer 2's circuit breaker
# produces when a portal call fails without blocking the run.
# ---------------------------------------------------------------------------


class MatchStatus(str, Enum):
    MATCH = "match"
    MINOR_DISCREPANCY = "minor_discrepancy"
    MAJOR_DISCREPANCY = "major_discrepancy"
    UNVERIFIABLE = "unverifiable"
    PORTAL_UNAVAILABLE = "portal_unavailable"


class RequirementStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Input: one per requirement, produced by Layer 3 (or hand-built for now)
# ---------------------------------------------------------------------------


@dataclass
class RequirementCheck:
    requirement_id: str
    requirement_name: str
    category: str  # e.g. "udyam", "gstn", "pan", "epfo", "blacklist", ...
    mandatory: bool
    match_status: MatchStatus
    weight: float = 1.0
    bidder_value: str | None = None
    portal_value: str | None = None
    extraction_confidence: float | None = None  # from Layer 1 OCR/LLM extraction
    portal_confidence: float | None = None  # from Layer 2 adapter
    evidence_refs: list[str] = field(default_factory=list)
    notes: str | None = None


# ---------------------------------------------------------------------------
# Output: per-requirement result + bidder-level report
# ---------------------------------------------------------------------------


@dataclass
class RuleResult:
    requirement_id: str
    requirement_name: str
    category: str
    status: RequirementStatus
    reason: str
    evidence_refs: list[str]
    weight: float
    mandatory: bool


@dataclass
class ComplianceReport:
    bidder_id: str
    overall_score: float  # 0-100
    risk_level: RiskLevel
    requirement_results: list[RuleResult]
    mandatory_failures: list[str]  # requirement_ids, for a fast eligibility check
    recommendation: str
    generated_at: datetime


# ---------------------------------------------------------------------------
# Config thresholds — pulled to the top so judges/teammates can see the rules
# are legible and tunable, not buried magic numbers.
# ---------------------------------------------------------------------------

LOW_CONFIDENCE_THRESHOLD = 0.65  # below this, force NEEDS_REVIEW regardless of match_status
MANDATORY_FAIL_SCORE_CAP = 40.0  # score can't exceed this if any mandatory requirement fails
NEEDS_REVIEW_PARTIAL_CREDIT = 0.5  # a NEEDS_REVIEW item counts as half-weight toward the score

RISK_SCORE_HIGH_CEILING = 60.0
RISK_SCORE_MEDIUM_CEILING = 85.0


# ---------------------------------------------------------------------------
# Rule evaluation — Tier-independent: doesn't matter if match_status came from
# Tier 1 exact match, Tier 2 fuzzy match, or Tier 3 LLM reconciliation. Layer 4
# only cares about the final match_status, keeping it decoupled from Layer 3.
# ---------------------------------------------------------------------------


def evaluate_requirement(check: RequirementCheck) -> RuleResult:
    """Turn one RequirementCheck into one explainable RuleResult."""

    low_confidence = (
                             check.extraction_confidence is not None
                             and check.extraction_confidence < LOW_CONFIDENCE_THRESHOLD
                     ) or (
                             check.portal_confidence is not None
                             and check.portal_confidence < LOW_CONFIDENCE_THRESHOLD
                     )

    if check.match_status == MatchStatus.PORTAL_UNAVAILABLE:
        status = RequirementStatus.NEEDS_REVIEW
        reason = (
            f"Portal source for '{check.requirement_name}' was unavailable at "
            f"verification time; could not confirm against submitted value."
        )
    elif check.match_status == MatchStatus.UNVERIFIABLE:
        status = RequirementStatus.NEEDS_REVIEW
        reason = (
            f"'{check.requirement_name}' could not be conclusively verified "
            f"(ambiguous match between submitted and portal values)."
        )
    elif low_confidence:
        status = RequirementStatus.NEEDS_REVIEW
        conf = check.extraction_confidence if check.extraction_confidence is not None else check.portal_confidence
        reason = (
            f"Low confidence ({conf:.0%}) in extracted/retrieved data for "
            f"'{check.requirement_name}'; flagged for manual review rather than "
            f"auto-passed or auto-failed."
        )
    elif check.match_status == MatchStatus.MATCH:
        status = RequirementStatus.PASS
        reason = f"'{check.requirement_name}' matches submitted value against portal record."
    elif check.match_status == MatchStatus.MINOR_DISCREPANCY:
        status = RequirementStatus.PASS
        reason = (
            f"'{check.requirement_name}' has a minor discrepancy (e.g. formatting, "
            f"casing) between submitted and portal values; treated as a pass."
        )
    elif check.match_status == MatchStatus.MAJOR_DISCREPANCY:
        status = RequirementStatus.FAIL
        reason = (
            f"'{check.requirement_name}' has a major discrepancy between submitted "
            f"value ({check.bidder_value!r}) and portal value ({check.portal_value!r})."
        )
    else:  # pragma: no cover - exhaustive by enum, defensive fallback
        status = RequirementStatus.NEEDS_REVIEW
        reason = f"Unrecognized match status for '{check.requirement_name}'."

    return RuleResult(
        requirement_id=check.requirement_id,
        requirement_name=check.requirement_name,
        category=check.category,
        status=status,
        reason=reason,
        evidence_refs=check.evidence_refs,
        weight=check.weight,
        mandatory=check.mandatory,
    )


# ---------------------------------------------------------------------------
# Score + risk + recommendation
# ---------------------------------------------------------------------------


def _compute_score(results: list[RuleResult]) -> tuple[float, list[str]]:
    total_weight = sum(r.weight for r in results) or 1.0
    earned = 0.0
    mandatory_failures: list[str] = []

    for r in results:
        if r.status == RequirementStatus.PASS:
            earned += r.weight
        elif r.status == RequirementStatus.NEEDS_REVIEW:
            earned += r.weight * NEEDS_REVIEW_PARTIAL_CREDIT
        # FAIL contributes 0

        if r.mandatory and r.status == RequirementStatus.FAIL:
            mandatory_failures.append(r.requirement_id)

    score = (earned / total_weight) * 100

    if mandatory_failures:
        score = min(score, MANDATORY_FAIL_SCORE_CAP)

    return round(score, 2), mandatory_failures


def _compute_risk(
        score: float,
        results: list[RuleResult],
        mandatory_failures: list[str],
) -> RiskLevel:
    if mandatory_failures:
        return RiskLevel.CRITICAL

    needs_review_count = sum(1 for r in results if r.status == RequirementStatus.NEEDS_REVIEW)
    fail_count = sum(1 for r in results if r.status == RequirementStatus.FAIL)

    if score < RISK_SCORE_HIGH_CEILING or fail_count >= 2:
        return RiskLevel.HIGH
    if score < RISK_SCORE_MEDIUM_CEILING or needs_review_count > 0:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _compute_recommendation(
        risk_level: RiskLevel,
        results: list[RuleResult],
        mandatory_failures: list[str],
) -> str:
    failed = [r for r in results if r.status == RequirementStatus.FAIL]
    needs_review = [r for r in results if r.status == RequirementStatus.NEEDS_REVIEW]

    if mandatory_failures:
        names = ", ".join(r.requirement_name for r in results if r.requirement_id in mandatory_failures)
        return (
            f"Recommend REJECT or request clarification: mandatory requirement(s) "
            f"failed verification — {names}. Officer review required before any "
            f"further processing."
        )

    if risk_level == RiskLevel.HIGH:
        names = ", ".join(r.requirement_name for r in failed[:3])
        return (
            f"Recommend CAUTION: multiple discrepancies found"
            f"{' (' + names + ')' if names else ''}. Manual review recommended "
            f"before proceeding."
        )

    if risk_level == RiskLevel.MEDIUM:
        parts = []
        if needs_review:
            parts.append(f"{len(needs_review)} item(s) need manual review")
        if failed:
            parts.append(f"{len(failed)} item(s) failed")
        detail = "; ".join(parts) if parts else "minor discrepancies present"
        return f"Recommend PROCEED WITH REVIEW: {detail}. No mandatory blockers found."

    return "Recommend PROCEED: all requirements verified with no significant discrepancies."


def score_bidder(bidder_id: str, checks: list[RequirementCheck]) -> ComplianceReport:
    """Entry point. Run the rule engine over a bidder's requirement checks and
    produce a full ComplianceReport (score, risk, per-requirement breakdown,
    recommendation). This is what the future verification_orchestrator.py and
    /bidder/verify endpoint will call once Layer 2/3 feed it real data."""

    results = [evaluate_requirement(c) for c in checks]
    score, mandatory_failures = _compute_score(results)
    risk_level = _compute_risk(score, results, mandatory_failures)
    recommendation = _compute_recommendation(risk_level, results, mandatory_failures)

    return ComplianceReport(
        bidder_id=bidder_id,
        overall_score=score,
        risk_level=risk_level,
        requirement_results=results,
        mandatory_failures=mandatory_failures,
        recommendation=recommendation,
        generated_at=datetime.now(timezone.utc),
    )