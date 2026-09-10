import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class RequirementStatus(str, PyEnum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"


class RiskLevel(str, PyEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ComplianceResult(Base):
    __tablename__ = "compliance_results"

    result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bidders.bidder_id", ondelete="CASCADE"))
    requirement_id: Mapped[str] = mapped_column(String, nullable=False)
    # e.g. "gstn_match", "udyam_validity", "debarment_check"
    status: Mapped[RequirementStatus] = mapped_column(PgEnum(RequirementStatus, name="requirement_status"), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)          # per-requirement or overall %
    risk_level: Mapped[RiskLevel | None] = mapped_column(PgEnum(RiskLevel, name="risk_level"), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"bidder_value": ..., "portal_value": ..., "source_doc_id": ..., "source_response_id": ...}
    remarks: Mapped[str | None] = mapped_column(String, nullable=True)  # plain-English reason
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bidder: Mapped["Bidder"] = relationship(back_populates="compliance_results")