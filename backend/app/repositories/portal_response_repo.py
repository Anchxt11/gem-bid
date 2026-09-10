import uuid
from sqlalchemy import select

from backend.app.models.portal_response import PortalResponse
from backend.app.repositories.base_repo import BaseRepository


class PortalResponseRepository(BaseRepository[PortalResponse]):
    model = PortalResponse

    async def list_by_bidder(self, bidder_id: uuid.UUID) -> list[PortalResponse]:
        result = await self.db.execute(select(PortalResponse).where(PortalResponse.bidder_id == bidder_id))
        return list(result.scalars().all())

    async def get_latest_by_portal(self, bidder_id: uuid.UUID, portal_name: str) -> PortalResponse | None:
        # useful later for the 24h TTL cache check mentioned in your architecture doc
        result = await self.db.execute(
            select(PortalResponse)
            .where(PortalResponse.bidder_id == bidder_id, PortalResponse.portal_name == portal_name)
            .order_by(PortalResponse.fetched_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()