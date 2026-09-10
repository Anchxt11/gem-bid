import uuid

from fastapi import HTTPException, status

from backend.app.repositories.document_repo import DocumentRepository
from backend.app.schemas.document_sc import DocumentCreate, DocumentRead
from backend.app.services.audit_service import AuditService


class DocumentService:
    def __init__(self, document_repo: DocumentRepository, audit_service: AuditService):
        self.document_repo = document_repo
        self.audit_service = audit_service

    async def create_document(self, data: DocumentCreate, actor: str) -> DocumentRead:
        document = await self.document_repo.create(data.model_dump())
        await self.audit_service.log_action(
            entity_type="document",
            entity_id=document.doc_id,
            action="uploaded",
            actor=actor,
            log_metadata={"doc_type": data.doc_type.value, "bidder_id": str(data.bidder_id)},
        )
        return DocumentRead.model_validate(document)

    async def get_document(self, doc_id: uuid.UUID) -> DocumentRead:
        document = await self.document_repo.get(doc_id)
        if document is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        return DocumentRead.model_validate(document)

    async def list_by_bidder(self, bidder_id: uuid.UUID) -> list[DocumentRead]:
        documents = await self.document_repo.list_by_bidder(bidder_id)
        return [DocumentRead.model_validate(d) for d in documents]

    async def delete_document(self, doc_id: uuid.UUID, actor: str) -> None:
        deleted = await self.document_repo.delete(doc_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        await self.audit_service.log_action(
            entity_type="document",
            entity_id=doc_id,
            action="deleted",
            actor=actor,
        )