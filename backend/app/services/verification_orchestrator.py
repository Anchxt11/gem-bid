import asyncio
import uuid

from backend.app.pipeline.portal_integration.base import PortalAdapter, PortalVerificationStatus
from backend.app.repositories.bidder_repo import BidderRepository
from backend.app.repositories.portal_response_repo import PortalResponseRepository
from backend.app.services.audit_service import AuditService


class VerificationOrchestrator:
    """
    The single seam that knows the pipeline has multiple stages.
    Right now it only runs Layer 2 (portal integration) and persists
    results — Layer 3 (reconciliation) and Layer 4 (scoring) get added
    here as their own steps once built, without changing the API route
    that calls this class.
    """

    def __init__(
        self,
        bidder_repo: BidderRepository,
        portal_response_repo: PortalResponseRepository,
        audit_service: AuditService,
        adapters: list[PortalAdapter],
    ):
        self.bidder_repo = bidder_repo
        self.portal_response_repo = portal_response_repo
        self.audit_service = audit_service
        self.adapters = adapters

    async def run_verification(self, bidder_id: uuid.UUID, actor: str) -> dict:
        bidder = await self.bidder_repo.get(bidder_id)
        if bidder is None:
            raise ValueError(f"Bidder {bidder_id} not found")

        bidder_data = {**bidder.company_details, **bidder.contact_info}

        # Layer 2 — hit every configured portal concurrently
        results = await asyncio.gather(
            *(adapter.verify(bidder_data) for adapter in self.adapters),
            return_exceptions=True,   # one portal failing shouldn't kill the whole run
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

        await self.audit_service.log_action(
            entity_type="bidder",
            entity_id=bidder_id,
            action="verification_run",
            actor=actor,
            log_metadata={"portals_checked": [a.source_name for a in self.adapters]},
        )

        # Layers 3/4 not built yet — return raw portal results so the
        # frontend has something real to render against in the meantime.
        # TODO: replace this block with real reconciliation + scoring output
        # once Layer 3/4 exist, without changing this method's signature.
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
            "compliance_score": None,     # placeholder until Layer 4 exists
            "risk_level": None,           # placeholder until Layer 4 exists
            "recommendation": "Pipeline stub — scoring not yet implemented.",
        }