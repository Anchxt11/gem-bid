import uuid
from sqlalchemy import select

from backend.app.models.document import Document
from backend.app.repositories.base_repo import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    model = Document

    async def list_by_bidder(self, bidder_id: uuid.UUID) -> list[Document]:
        result = await self.db.execute(select(Document).where(Document.bidder_id == bidder_id))
        return list(result.scalars().all())