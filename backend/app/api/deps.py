from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.repositories.bidder_repo import BidderRepository
from backend.app.repositories.audit_log_repo import AuditLogRepository
from backend.app.services.audit_service import AuditService
from backend.app.services.bidder_service import BidderService
from backend.app.repositories.document_repo import DocumentRepository
from backend.app.services.document_service import DocumentService


async def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    return AuditService(AuditLogRepository(db))


async def get_bidder_service(
    db: AsyncSession = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> BidderService:
    return BidderService(BidderRepository(db), audit_service)

async def get_document_service(
    db: AsyncSession = Depends(get_db),
    audit_service: AuditService = Depends(get_audit_service),
) -> DocumentService:
    return DocumentService(DocumentRepository(db), audit_service)