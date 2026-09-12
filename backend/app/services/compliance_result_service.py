import uuid

from backend.app.models.compliance_result import RequirementStatus as DbRequirementStatus
from backend.app.models.compliance_result import RiskLevel as DbRiskLevel
from backend.app.pipeline.scoring.base import RequirementCheck, RiskLevel as EngineRiskLevel, score_bidder
from backend.app.repositories.compliance_result_repo import ComplianceResultRepository
from backend.app.schemas.compliance_result_sc import ComplianceResultRead
from backend.app.services.audit_service import AuditService

# Your DB's RiskLevel enum has no CRITICAL tier yet (LOW/MEDIUM/HIGH only).
# The scoring engine uses CRITICAL specifically to mean "a mandatory
# requirement failed, bidder is ineligible" - a stronger signal than a
# merely-risky HIGH bidder. We map it down to HIGH only for the DB row;
# the API response (see compliance.py) still returns the full CRITICAL
# distinction so the officer/dashboard don't lose that signal. If you'd
# rather store it properly, add CRITICAL to the Postgres enum via an
# Alembic migration and remove this mapping.
_ENGINE_TO_DB_RISK = {
    EngineRiskLevel.LOW: DbRiskLevel.LOW,
    EngineRiskLevel.MEDIUM: DbRiskLevel.MEDIUM,
    EngineRiskLevel.HIGH: DbRiskLevel.HIGH,
    EngineRiskLevel.CRITICAL: DbRiskLevel.HIGH,
}

# Engine's RequirementStatus values ("pass"/"fail"/"needs_review") already
# match the DB enum's values exactly, so this is just a type conversion.
_ENGINE_TO_DB_STATUS = {
    "pass": DbRequirementStatus.PASS,
    "fail": DbRequirementStatus.FAIL,
    "needs_review": DbRequirementStatus.NEEDS_REVIEW,
}


class ComplianceResultService:
    def __init__(self, compliance_repo: ComplianceResultRepository, audit_service: AuditService):
        self.compliance_repo = compliance_repo
        self.audit_service = audit_service

    async def run_scoring(
            self,
            bidder_id: uuid.UUID,
            checks: list[RequirementCheck],
            actor: str,
    ) -> dict:
        """
        Runs the Layer 4 rule engine over `checks` (today: hand-built/API-
        supplied fake data standing in for Layer 3's real output later),
        writes one compliance_results row per requirement, logs one audit
        entry for the whole run, and returns the full report shape the
        dashboard needs (including the CRITICAL risk tier the DB can't
        store yet).
        """
        report = score_bidder(str(bidder_id), checks)
        db_risk = _ENGINE_TO_DB_RISK[report.risk_level]

        saved_rows = []
        for r in report.requirement_results:
            evidence = {
                "requirement_name": r.requirement_name,
                "category": r.category,
                "mandatory": r.mandatory,
                "weight": r.weight,
                "evidence_refs": r.evidence_refs,
            }
            row = await self.compliance_repo.create(
                {
                    "bidder_id": bidder_id,
                    "requirement_id": r.requirement_id,
                    "status": _ENGINE_TO_DB_STATUS[r.status.value],
                    "score": report.overall_score,
                    "risk_level": db_risk,
                    "evidence": evidence,
                    "remarks": r.reason,
                }
            )
            saved_rows.append(ComplianceResultRead.model_validate(row))

        await self.audit_service.log_action(
            entity_type="bidder",
            entity_id=bidder_id,
            action="compliance_scored",
            actor=actor,
            log_metadata={
                "overall_score": report.overall_score,
                "risk_level": report.risk_level.value,
                "mandatory_failures": report.mandatory_failures,
                "recommendation": report.recommendation,
            },
        )

        return {
            "bidder_id": bidder_id,
            "overall_score": report.overall_score,
            "risk_level": report.risk_level.value,
            "recommendation": report.recommendation,
            "results": saved_rows,
        }

    async def get_summary(self, bidder_id: uuid.UUID) -> list[ComplianceResultRead]:
        rows = await self.compliance_repo.list_by_bidder(bidder_id)
        return [ComplianceResultRead.model_validate(r) for r in rows]
