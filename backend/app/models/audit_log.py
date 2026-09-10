import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)   # "bidder" | "document" | "compliance_result" | ...
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String, nullable=False)        # "created" | "verified" | "overridden" | ...
    actor: Mapped[str] = mapped_column(String, nullable=False)         # officer id / "system" for pipeline-generated entries
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    prev_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    curr_hash: Mapped[str] = mapped_column(String, nullable=False)
    log_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # note: named log_metadata not metadata — SQLAlchemy reserves Base.metadata