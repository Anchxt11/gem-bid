import uuid

from fastapi import APIRouter, Depends, Header

from backend.app.api.deps import get_bidder_service
from backend.app.schemas.bidder_sc import BidderCreate, BidderUpdate, BidderRead
from backend.app.services.bidder_service import BidderService

router = APIRouter(prefix="/bidders", tags=["bidders"])


@router.post("/", response_model=BidderRead, status_code=201)
async def create_bidder(
    data: BidderCreate,
    service: BidderService = Depends(get_bidder_service),
    actor: str = Header(default="system", alias="X-Actor"),
):
    return await service.create_bidder(data, actor=actor)


@router.get("/", response_model=list[BidderRead])
async def list_bidders(
    skip: int = 0,
    limit: int = 100,
    service: BidderService = Depends(get_bidder_service),
):
    return await service.list_bidders(skip, limit)


@router.get("/{bidder_id}", response_model=BidderRead)
async def get_bidder(
    bidder_id: uuid.UUID,
    service: BidderService = Depends(get_bidder_service),
):
    return await service.get_bidder(bidder_id)


@router.delete("/{bidder_id}", status_code=204)
async def delete_bidder(
    bidder_id: uuid.UUID,
    service: BidderService = Depends(get_bidder_service),
    actor: str = Header(default="system", alias="X-Actor"),
):
    await service.delete_bidder(bidder_id, actor=actor)