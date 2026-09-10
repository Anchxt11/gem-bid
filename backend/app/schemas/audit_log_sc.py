import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AuditLogCreate(BaseModel):
    entity_type: str
    entity_id: uuid.UUID
    action: str
    actor: str
    log_metadata: dict | None = None
    # prev_hash / curr_hash deliberately excluded — the audit service computes
    # these itself, never accepts them from a caller


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    action: str
    actor: str
    timestamp: datetime
    prev_hash: str | None = None
    curr_hash: str
    log_metadata: dict | None = None