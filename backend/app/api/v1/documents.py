import uuid

from fastapi import APIRouter, Depends, Header

from backend.app.api.deps import get_document_service
from backend.app.schemas.document_sc import DocumentCreate, DocumentRead
from backend.app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/", response_model=DocumentRead, status_code=201)
async def create_document(
    data: DocumentCreate,
    service: DocumentService = Depends(get_document_service),
    actor: str = Header(default="system", alias="X-Actor"),
):
    return await service.create_document(data, actor=actor)


@router.get("/{doc_id}", response_model=DocumentRead)
async def get_document(
    doc_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
):
    return await service.get_document(doc_id)


@router.get("/bidder/{bidder_id}", response_model=list[DocumentRead])
async def list_documents_for_bidder(
    bidder_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
):
    return await service.list_by_bidder(bidder_id)


@router.delete("/{doc_id}", status_code=204)
async def delete_document(
    doc_id: uuid.UUID,
    service: DocumentService = Depends(get_document_service),
    actor: str = Header(default="system", alias="X-Actor"),
):
    await service.delete_document(doc_id, actor=actor)