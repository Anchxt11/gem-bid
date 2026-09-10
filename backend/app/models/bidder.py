import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class BidderStatus(str, PyEnum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    VERIFIED = "verified"
    REJECTED = "rejected"


class Bidder(Base):
    __tablename__ = "bidders"

    bidder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_details: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # e.g. {"legal_name": ..., "gstin": ..., "pan": ..., "udyam_number": ...}
    contact_info: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # e.g. {"email": ..., "phone": ..., "address": ...}
    status: Mapped[BidderStatus] = mapped_column(
        PgEnum(BidderStatus, name="bidder_status"),
        default=BidderStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(back_populates="bidder", cascade="all, delete-orphan")
    portal_responses: Mapped[list["PortalResponse"]] = relationship(back_populates="bidder", cascade="all, delete-orphan")
    compliance_results: Mapped[list["ComplianceResult"]] = relationship(back_populates="bidder", cascade="all, delete-orphan")