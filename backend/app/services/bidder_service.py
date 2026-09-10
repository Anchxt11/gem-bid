import uuid

from fastapi import HTTPException, status

from backend.app.repositories.bidder_repo import BidderRepository
from backend.app.schemas.bidder_sc import BidderCreate, BidderUpdate, BidderRead
from backend.app.services.audit_service import AuditService


class BidderService:
    def __init__(self, bidder_repo: BidderRepository, audit_service: AuditService):
        self.bidder_repo = bidder_repo
        self.audit_service = audit_service

    async def create_bidder(self, data: BidderCreate, actor: str) -> BidderRead:
        bidder = await self.bidder_repo.create(data.model_dump())
        await self.audit_service.log_action(
            entity_type="bidder",
            entity_id=bidder.bidder_id,
            action="created",
            actor=actor,
        )
        return BidderRead.model_validate(bidder)

    async def get_bidder(self, bidder_id: uuid.UUID) -> BidderRead:
        bidder = await self.bidder_repo.get(bidder_id)
        if bidder is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bidder not found")
        return BidderRead.model_validate(bidder)

    async def list_bidders(self, skip: int = 0, limit: int = 100) -> list[BidderRead]:
        bidders = await self.bidder_repo.list(skip, limit)
        return [BidderRead.model_validate(b) for b in bidders]

    async def delete_bidder(self, bidder_id: uuid.UUID, actor: str) -> None:
        deleted = await self.bidder_repo.delete(bidder_id)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bidder not found")
        await self.audit_service.log_action(
            entity_type="bidder",
            entity_id=bidder_id,
            action="deleted",
            actor=actor,
        )