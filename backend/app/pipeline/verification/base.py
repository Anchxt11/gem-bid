"""
pipeline/verification/base.py

Layer 3 — AI Verification Engine (reconciliation).

Job: compare what the bidder submitted against what Layer 2's portal
adapters retrieved, and turn that into a RequirementCheck — Layer 4's
input type. This module never calls a portal itself and never computes
a compliance score; it sits strictly between Layer 2 and Layer 4.

Three-tier logic per the architecture doc, cheapest first:
  Tier 1 — exact match (no AI): normalized string equality.
  Tier 2 — fuzzy match (no AI): rapidfuzz similarity score.
  Tier 3 — LLM call: only for genuinely ambiguous fuzzy scores. Implemented
           here as a swappable interface (LLMReconciler) with a disclosed,
           honest stub (StubLLMReconciler) as the default — same pattern
           as Layer 2's PortalAdapter mocks. Swapping in a real LLM call
           later means writing one new class, not touching this file's
           logic.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone


import httpx
from rapidfuzz import fuzz

from backend.app.pipeline.portal_integration.base import (
    PortalVerificationResult,
    PortalVerificationStatus,
)
from backend.app.pipeline.scoring.base import MatchStatus, RequirementCheck
from backend.app.pipeline.verification.requirement import RequirementDefinition

# Tier 2 thresholds — tunable. Above FUZZY_MATCH_THRESHOLD: close enough to
# call a minor discrepancy (formatting/suffix differences). Below
# FUZZY_MISMATCH_THRESHOLD: different enough to call a major discrepancy
# outright, no need to spend an LLM call on it. Between the two: genuinely
# ambiguous, escalate to Tier 3.
FUZZY_MATCH_THRESHOLD = 90.0
FUZZY_MISMATCH_THRESHOLD = 70.0


def _normalize(value: str | None) -> str:
    return (value or "").strip().upper()


class LLMReconciler(ABC):
    """Tier 3. Every implementation — stub or real — returns the same shape,
    so the reconciliation engine below never needs to know which one it has."""

    @abstractmethod
    async def reconcile_ambiguous_name(
            self, bidder_name: str, portal_name: str, context: dict
    ) -> tuple[MatchStatus, str]:
        ...


class StubLLMReconciler(LLMReconciler):
    """Default Tier 3. Disclosed stand-in: rather than guess at an ambiguous
    name match, this flags it for manual officer review. Per the architecture
    doc, real LLM reconciliation is intentionally the last piece built — this
    keeps the rest of the pipeline honest and functional in the meantime."""

    async def reconcile_ambiguous_name(
            self, bidder_name: str, portal_name: str, context: dict
    ) -> tuple[MatchStatus, str]:
        return (
            MatchStatus.UNVERIFIABLE,
            f"Name similarity between submitted value '{bidder_name}' and portal "
            f"value '{portal_name}' was ambiguous — neither a clear match nor an "
            f"obvious mismatch. Tier 3 LLM reconciliation is not yet wired in; "
            f"flagged for manual officer review rather than guessed.",
        )

class OllamaLLMReconciler(LLMReconciler):
    def __init__(self, model: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

        async def is_available(self) -> bool:
            try:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.get(f"{self.base_url}/api/tags")
                    return response.status_code == 200
            except Exception:
                return False

    async def reconcile_ambiguous_name(self, bidder_name, portal_name, context):
        prompt = (
            "You are checking government procurement bidder identity data. "
            "Two names are being compared: one submitted by the bidder, one "
            "retrieved from a government portal. Decide if they refer to the "
            "same legal entity.\n\n"
            f"Submitted name: {bidder_name}\n"
            f"Portal name: {portal_name}\n"
            f"Requirement being checked: {context.get('requirement', 'unknown')}\n\n"
            "Respond with ONLY a JSON object, no other text, in exactly this shape:\n"
            '{"match_status": "match" | "minor_discrepancy" | "major_discrepancy" | "unverifiable", '
            '"reason": "one sentence explaining your decision"}'
        )
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                content = response.json()["message"]["content"]
                parsed = json.loads(content)
            status_str = parsed.get("match_status", "unverifiable")
            reason = parsed.get("reason", "No reason provided by model.")
            match_status = MatchStatus(status_str)
            return match_status, f"[Tier 3 - local Llama] {reason}"
        except Exception as exc:
            return (
                MatchStatus.UNVERIFIABLE,
                f"Tier 3 LLM call failed ({exc.__class__.__name__}); flagged for manual officer review rather than guessed.",
            )

async def reconcile(
        bidder_data: dict,
        portal_result: PortalVerificationResult,
        definition: RequirementDefinition,
        llm_reconciler: LLMReconciler | None = None,


) -> RequirementCheck:
    """Turn one portal's result into one Layer 4 RequirementCheck."""

    llm_reconciler = llm_reconciler or StubLLMReconciler()

    if portal_result.status == PortalVerificationStatus.UNAVAILABLE:
        return RequirementCheck(
            requirement_id=definition.requirement_id,
            requirement_name=definition.requirement_name,
            category=definition.category,
            mandatory=definition.mandatory,
            weight=definition.weight,
            match_status=MatchStatus.PORTAL_UNAVAILABLE,
            portal_confidence=portal_result.confidence,
            evidence_refs=[f"portal:{definition.portal_source}"],
            notes=str(portal_result.raw_response.get("error", "portal unavailable")),
        )

    if portal_result.status == PortalVerificationStatus.NOT_FOUND:
        return RequirementCheck(
            requirement_id=definition.requirement_id,
            requirement_name=definition.requirement_name,
            category=definition.category,
            mandatory=definition.mandatory,
            weight=definition.weight,
            match_status=MatchStatus.MAJOR_DISCREPANCY,
            portal_confidence=portal_result.confidence,
            evidence_refs=[f"portal:{definition.portal_source}"],
            notes=f"Bidder-submitted identifier for '{definition.requirement_name}' "
                  f"was not found on the portal.",
        )

    fields = portal_result.retrieved_fields

    if definition.kind == "listing":
        if not fields:
            return RequirementCheck(
                requirement_id=definition.requirement_id,
                requirement_name=definition.requirement_name,
                category=definition.category,
                mandatory=definition.mandatory,
                weight=definition.weight,
                match_status=MatchStatus.MATCH,
                portal_value="not listed",
                portal_confidence=portal_result.confidence,
                evidence_refs=[f"portal:{definition.portal_source}"],
            )
        reason = fields.get("reason", "listed on debarment/blacklist register")
        return RequirementCheck(
            requirement_id=definition.requirement_id,
            requirement_name=definition.requirement_name,
            category=definition.category,
            mandatory=definition.mandatory,
            weight=definition.weight,
            match_status=MatchStatus.MAJOR_DISCREPANCY,
            portal_value=f"listed: {reason}",
            portal_confidence=portal_result.confidence,
            evidence_refs=[f"portal:{definition.portal_source}"],
            notes=f"Bidder appears on the debarment list: {reason}.",
        )

    is_active = True
    inactive_reason = None

    if definition.status_field:
        status_value = _normalize(fields.get(definition.status_field))
        is_active = status_value.lower() in definition.active_values
        if not is_active:
            inactive_reason = f"status is '{fields.get(definition.status_field)}'"
    elif definition.date_field and fields.get(definition.date_field):
        try:
            expiry = date.fromisoformat(fields[definition.date_field])
            is_active = expiry >= datetime.now(timezone.utc).date()
            if not is_active:
                inactive_reason = f"validity expired on {expiry.isoformat()}"
        except ValueError:
            pass

    if not is_active:
        return RequirementCheck(
            requirement_id=definition.requirement_id,
            requirement_name=definition.requirement_name,
            category=definition.category,
            mandatory=definition.mandatory,
            weight=definition.weight,
            match_status=MatchStatus.MAJOR_DISCREPANCY,
            portal_value=str(fields.get(definition.status_field or definition.date_field)),
            portal_confidence=portal_result.confidence,
            evidence_refs=[f"portal:{definition.portal_source}"],
            notes=f"'{definition.requirement_name}' found on portal but {inactive_reason}.",
        )

    if not definition.name_field:
        return RequirementCheck(
            requirement_id=definition.requirement_id,
            requirement_name=definition.requirement_name,
            category=definition.category,
            mandatory=definition.mandatory,
            weight=definition.weight,
            match_status=MatchStatus.MATCH,
            portal_confidence=portal_result.confidence,
            evidence_refs=[f"portal:{definition.portal_source}"],
        )

    bidder_name = _normalize(bidder_data.get(definition.bidder_name_field))
    portal_name = _normalize(fields.get(definition.name_field))

    if not bidder_name or not portal_name:
        match_status, notes = MatchStatus.UNVERIFIABLE, "Missing name on one side of the comparison."
    elif bidder_name == portal_name:
        match_status, notes = MatchStatus.MATCH, None
    else:
        similarity = fuzz.token_sort_ratio(bidder_name, portal_name)
        if similarity >= FUZZY_MATCH_THRESHOLD:
            match_status = MatchStatus.MINOR_DISCREPANCY
            notes = f"Name similarity {similarity:.0f}% — likely formatting/suffix difference only."
        elif similarity <= FUZZY_MISMATCH_THRESHOLD:
            match_status = MatchStatus.MAJOR_DISCREPANCY
            notes = f"Name similarity only {similarity:.0f}% — likely a different entity."
        else:
            match_status, notes = await llm_reconciler.reconcile_ambiguous_name(
                bidder_name, portal_name, context={"requirement": definition.requirement_name}
            )

    return RequirementCheck(
        requirement_id=definition.requirement_id,
        requirement_name=definition.requirement_name,
        category=definition.category,
        mandatory=definition.mandatory,
        weight=definition.weight,
        match_status=match_status,
        bidder_value=bidder_data.get("legal_name"),
        portal_value=fields.get(definition.name_field),
        portal_confidence=portal_result.confidence,
        evidence_refs=[f"portal:{definition.portal_source}"],
        notes=notes,
    )
