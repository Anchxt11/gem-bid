from backend.app.models.bidder import Bidder
from backend.app.repositories.base_repo import BaseRepository


class BidderRepository(BaseRepository[Bidder]):
    model = Bidder

    # add bidder-specific queries here as you need them, e.g.
    # async def get_by_status(self, status): ...