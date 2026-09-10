import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class PortalStatus(str, PyEnum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"   # circuit breaker / timeout
    ERROR = "error"


class PortalResponse(Base):
    __tablename__ = "portal_responses"

    response_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bidders.bidder_id", ondelete="CASCADE"))
    portal_name: Mapped[str] = mapped_column(String, nullable=False)
    # "digilocker" | "gstn" | "pan" | "udyam" | "epfo" | "esic" | "mca21" | "nsic" | "startup_india" | "debarment_list"
    status: Mapped[PortalStatus] = mapped_column(PgEnum(PortalStatus, name="portal_status"), nullable=False)
    response_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # normalized PortalVerificationResult payload: retrieved_fields, confidence, raw_response
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bidder: Mapped["Bidder"] = relationship(back_populates="portal_responses")