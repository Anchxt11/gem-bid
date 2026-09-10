import uuid
from sqlalchemy import select

from backend.app.models.compliance_result import ComplianceResult
from backend.app.repositories.base_repo import BaseRepository


class ComplianceResultRepository(BaseRepository[ComplianceResult]):
    model = ComplianceResult

    async def list_by_bidder(self, bidder_id: uuid.UUID) -> list[ComplianceResult]:
        result = await self.db.execute(select(ComplianceResult).where(ComplianceResult.bidder_id == bidder_id))
        return list(result.scalars().all())