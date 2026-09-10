import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base


class DocumentType(str, PyEnum):
    UDYAM_CERTIFICATE = "udyam_certificate"
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    EPFO_CHALLAN = "epfo_challan"
    MCA21_CERTIFICATE = "mca21_certificate"
    STARTUP_INDIA_CERT = "startup_india_cert"
    OTHER = "other"


class Document(Base):
    __tablename__ = "documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bidder_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bidders.bidder_id", ondelete="CASCADE"))
    doc_type: Mapped[DocumentType] = mapped_column(PgEnum(DocumentType, name="document_type"), nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    extracted_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # per-field confidence scores live inside extracted_data, e.g.
    # {"fields": {...}, "confidence": {"gstin": 0.97, "name": 0.62}}
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bidder: Mapped["Bidder"] = relationship(back_populates="documents")