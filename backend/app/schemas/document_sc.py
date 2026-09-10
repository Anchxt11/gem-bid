import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from backend.app.models.document import DocumentType


class DocumentBase(BaseModel):
    doc_type: DocumentType


class DocumentCreate(DocumentBase):
    bidder_id: uuid.UUID
    file_path: str


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    doc_id: uuid.UUID
    bidder_id: uuid.UUID
    file_path: str
    extracted_data: dict | None = None
    uploaded_at: datetime