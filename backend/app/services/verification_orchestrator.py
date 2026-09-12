import asyncio
import uuid

from backend.app.models.compliance_result import RequirementStatus as DbRequirementStatus
from backend.app.models.compliance_result import RiskLevel as DbRiskLevel
from backend.app.pipeline.portal_integration.base import PortalAdapter, PortalVerificationStatus
from backend.app.pipeline.scoring.base import RiskLevel as EngineRiskLevel, score_bidder
from backend.app.pipeline.verification.base import LLMReconciler, reconcile
from backend.app.pipeline.verification.requirement import REQUIREMENTS
from backend.app.repositories.bidder_repo import BidderRepository
from backend.app.repositories.compliance_result_repo import ComplianceResultRepository
from backend.app.repositories.portal_response_repo import PortalResponseRepository
from backend.app.services.audit_service import AuditService

# DB's RiskLevel enum has no CRITICAL tier (LOW/MEDIUM/HIGH only). The
# scoring engine's CRITICAL means "a mandatory requirement failed, bidder
# ineligible" — stronger than a merely-risky HIGH. Mapped down to HIGH only
# for storage; the API response below keeps the full CRITICAL distinction.
_ENGINE_TO_DB_RISK = {
    EngineRiskLevel.LOW: DbRiskLevel.LOW,
    EngineRiskLevel.MEDIUM: DbRiskLevel.MEDIUM,
    EngineRiskLevel.HIGH: DbRiskLevel.HIGH,
    EngineRiskLevel.CRITICAL: DbRiskLevel.HIGH,
}

# Engine's RequirementStatus values ("pass"/"fail"/"needs_review") already
# match the DB enum's values, so this is just a type conversion.
_ENGINE_TO_DB_STATUS = {
    "pass": DbRequirementStatus.PASS,
    "fail": DbRequirementStatus.FAIL,
    "needs_review": DbRequirementStatus.NEEDS_REVIEW,
}


class VerificationOrchestrator:
    """
    The single seam that knows the pipeline has multiple stages: Layer 2
    (portal integration) -> Layer 3 (reconciliation) -> Layer 4 (scoring),
    persisting results at each stage. The API route calling this class
    (`POST /bidder/{bidder_id}/verify`) never changed shape as these layers
    were added — only this method's internals grew.
    """

    def __init__(
            self,
            bidder_repo: BidderRepository,
            portal_response_repo: PortalResponseRepository,
            audit_service: AuditService,
            adapters: list[PortalAdapter],
            compliance_result_repo: ComplianceResultRepository | None = None,
            llm_reconciler: LLMReconciler | None = None,
    ):
        self.bidder_repo = bidder_repo
        self.portal_response_repo = portal_response_repo
        self.audit_service = audit_service
        self.adapters = adapters
        self.compliance_result_repo = compliance_result_repo
        self.llm_reconciler = llm_reconciler

    async def run_verification(self, bidder_id: uuid.UUID, actor: str) -> dict:
        bidder = await self.bidder_repo.get(bidder_id)
        if bidder is None:
            raise ValueError(f"Bidder {bidder_id} not found")

        bidder_data = {**bidder.company_details, **bidder.contact_info}

        # Layer 2 — hit every configured portal concurrently
        results = await asyncio.gather(
            *(adapter.verify(bidder_data) for adapter in self.adapters),
            return_exceptions=True,  # one portal failing shouldn't kill the whole run
        )

        persisted = []
        for adapter, result in zip(self.adapters, results):
            if isinstance(result, Exception):
                # circuit-breaker-style fallback: record as unavailable, don't crash
                row = await self.portal_response_repo.create({
                    "bidder_id": bidder_id,
                    "portal_name": adapter.source_name,
                    "status": PortalVerificationStatus.UNAVAILABLE,
                    "response_data": {"error": str(result)},
                })
            else:
                row = await self.portal_response_repo.create({
                    "bidder_id": bidder_id,
                    "portal_name": result.source,
                    "status": result.status,
                    "response_data": result.model_dump(mode="json"),
                })
            persisted.append(row)

        # Layer 3 — reconcile each portal result against what the bidder
        # submitted, using the requirement registry to know which fields
        # to compare for that portal. Adapters with no registry entry are
        # skipped rather than crashing (keeps this forward-compatible with
        # new adapters that haven't been added to the registry yet).
        checks = []
        for adapter, result in zip(self.adapters, results):
            if isinstance(result, Exception):
                continue  # already recorded as UNAVAILABLE above; nothing to reconcile
            definition = REQUIREMENTS.get(adapter.source_name)
            if definition is None:
                continue
            check = await reconcile(bidder_data, result, definition, self.llm_reconciler)
            checks.append(check)

        # Layer 4 — score the reconciled checks
        report = score_bidder(str(bidder_id), checks)

        saved_compliance_rows = []
        if self.compliance_result_repo is not None:
            db_risk = _ENGINE_TO_DB_RISK[report.risk_level]
            for r in report.requirement_results:
                row = await self.compliance_result_repo.create(
                    {
                        "bidder_id": bidder_id,
                        "requirement_id": r.requirement_id,
                        "status": _ENGINE_TO_DB_STATUS[r.status.value],
                        "score": report.overall_score,
                        "risk_level": db_risk,
                        "evidence": {
                            "requirement_name": r.requirement_name,
                            "category": r.category,
                            "mandatory": r.mandatory,
                            "weight": r.weight,
                            "evidence_refs": r.evidence_refs,
                        },
                        "remarks": r.reason,
                    }
                )
                saved_compliance_rows.append(row)

        await self.audit_service.log_action(
            entity_type="bidder",
            entity_id=bidder_id,
            action="verification_run",
            actor=actor,
            log_metadata={
                "portals_checked": [a.source_name for a in self.adapters],
                "overall_score": report.overall_score,
                "risk_level": report.risk_level.value,
                "mandatory_failures": report.mandatory_failures,
            },
        )

        return {
            "bidder_id": str(bidder_id),
            "portal_results": [
                {
                    "portal_name": r.portal_name,
                    "status": r.status.value if hasattr(r.status, "value") else r.status,
                    "response_data": r.response_data,
                    "fetched_at": r.fetched_at.isoformat(),
                }
                for r in persisted
            ],
            "requirement_results": [
                {
                    "requirement_id": r.requirement_id,
                    "requirement_name": r.requirement_name,
                    "category": r.category,
                    "mandatory": r.mandatory,
                    "status": r.status.value,
                    "reason": r.reason,
                    "evidence_refs": r.evidence_refs,
                }
                for r in report.requirement_results
            ],
            "compliance_score": report.overall_score,
            "risk_level": report.risk_level.value,
            # kept as plain str: can be "critical", which the DB enum doesn't have
            "recommendation": report.recommendation,
        }