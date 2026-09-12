import uuid

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from backend.app.api.deps import get_compliance_service
from backend.app.pipeline.scoring.base import MatchStatus, RequirementCheck
from backend.app.schemas.compliance_result_sc import ComplianceResultRead
from backend.app.services.compliance_result_service import ComplianceResultService

router = APIRouter(prefix="/compliance", tags=["compliance"])


# --- Request/response shapes for this endpoint only (not DB schemas) -------
# Until Layer 2/3 exist, the caller (you, testing via /docs or curl, or
# later the real orchestrator) supplies the reconciliation checks directly.
# This shape is identical to RequirementCheck in pipeline/scoring/base.py -
# swapping this out for real Layer 3 output later means no changes here,
# just a different caller.


class RequirementCheckIn(BaseModel):
    requirement_id: str
    requirement_name: str
    category: str
    mandatory: bool
    match_status: MatchStatus
    weight: float = 1.0
    bidder_value: str | None = None
    portal_value: str | None = None
    extraction_confidence: float | None = None
    portal_confidence: float | None = None
    evidence_refs: list[str] = []
    notes: str | None = None


class ComplianceRunRequest(BaseModel):
    checks: list[RequirementCheckIn]


class ComplianceRunResponse(BaseModel):
    bidder_id: uuid.UUID
    overall_score: float
    risk_level: str  # kept as plain str here since it can be "critical", which the DB enum doesn't have
    recommendation: str
    results: list[ComplianceResultRead]


@router.post("/{bidder_id}/run", response_model=ComplianceRunResponse)
async def run_compliance_scoring(
        bidder_id: uuid.UUID,
        payload: ComplianceRunRequest,
        x_actor: str = Header(default="system"),
        service: ComplianceResultService = Depends(get_compliance_service),
):
    checks = [RequirementCheck(**c.model_dump()) for c in payload.checks]
    return await service.run_scoring(bidder_id, checks, actor=x_actor)


@router.get("/{bidder_id}", response_model=list[ComplianceResultRead])
async def get_compliance_results(
        bidder_id: uuid.UUID,
        service: ComplianceResultService = Depends(get_compliance_service),
):
    return await service.get_summary(bidder_id)
