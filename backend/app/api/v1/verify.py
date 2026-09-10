import uuid

from fastapi import APIRouter, Depends, Header, HTTPException

from backend.app.api.deps import get_verification_orchestrator
from backend.app.services.verification_orchestrator import VerificationOrchestrator

router = APIRouter(prefix="/bidder", tags=["verification"])


@router.post("/{bidder_id}/verify")
async def verify_bidder(
    bidder_id: uuid.UUID,
    orchestrator: VerificationOrchestrator = Depends(get_verification_orchestrator),
    actor: str = Header(default="system", alias="X-Actor"),
):
    try:
        return await orchestrator.run_verification(bidder_id, actor=actor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))