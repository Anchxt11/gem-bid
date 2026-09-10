import uuid

from fastapi import APIRouter, Depends

from backend.app.api.deps import get_audit_service
from backend.app.schemas.audit_log_sc import AuditLogRead
from backend.app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/log", response_model=list[AuditLogRead])
async def get_audit_trail(
    entity_type: str,
    entity_id: uuid.UUID,
    service: AuditService = Depends(get_audit_service),
):
    return await service.get_trail(entity_type, entity_id)


@router.get("/verify-integrity")
async def verify_integrity(
    service: AuditService = Depends(get_audit_service),
) -> dict:
    is_valid = await service.verify_chain_integrity()
    return {"chain_valid": is_valid}