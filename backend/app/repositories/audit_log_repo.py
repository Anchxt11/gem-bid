import uuid
from sqlalchemy import select

from backend.app.models.audit_log import AuditLog
from backend.app.repositories.base_repo import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    async def list_by_entity(self, entity_type: str, entity_id: uuid.UUID) -> list[AuditLog]:
        result = await self.db.execute(
            select(AuditLog)
            .where(AuditLog.entity_type == entity_type, AuditLog.entity_id == entity_id)
            .order_by(AuditLog.timestamp.asc())
        )
        return list(result.scalars().all())

    async def get_latest(self) -> AuditLog | None:
        # needed by audit_service to fetch prev_hash for the next entry
        result = await self.db.execute(select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(1))
        return result.scalar_one_or_none()