import hashlib
import json
import uuid
from datetime import datetime, timezone

from backend.app.repositories.audit_log_repo import AuditLogRepository
from backend.app.schemas.audit_log_sc import AuditLogCreate, AuditLogRead


class AuditService:
    def __init__(self, audit_repo: AuditLogRepository):
        self.audit_repo = audit_repo

    async def log_action(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        actor: str,
        log_metadata: dict | None = None,
    ) -> AuditLogRead:
        """
        Every write-worthy event in the system funnels through here.
        This is the ONLY place curr_hash/prev_hash get computed — never
        let a caller pass these in, or the tamper-evidence is meaningless.
        """
        latest = await self.audit_repo.get_latest()
        prev_hash = latest.curr_hash if latest else None

        timestamp = datetime.now(timezone.utc)

        # Hash covers everything that matters about this entry, chained to
        # the previous entry's hash — changing any past row breaks every
        # hash after it, which is what makes tampering detectable.
        payload = {
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "action": action,
            "actor": actor,
            "timestamp": timestamp.isoformat(),
            "log_metadata": log_metadata,
            "prev_hash": prev_hash,
        }
        curr_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()

        entry = await self.audit_repo.create({
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "actor": actor,
            "timestamp": timestamp,
            "prev_hash": prev_hash,
            "curr_hash": curr_hash,
            "log_metadata": log_metadata,
        })
        return AuditLogRead.model_validate(entry)

    async def get_trail(self, entity_type: str, entity_id: uuid.UUID) -> list[AuditLogRead]:
        entries = await self.audit_repo.list_by_entity(entity_type, entity_id)
        return [AuditLogRead.model_validate(e) for e in entries]

    async def verify_chain_integrity(self) -> bool:
        """
        Walks the whole chain and recomputes each hash to confirm nothing
        was altered after the fact. Good demo feature for judges — you can
        literally show this returning False if someone edits a row directly
        in Postgres.
        """
        all_entries = await self.audit_repo.list(skip=0, limit=100000)
        all_entries.sort(key=lambda e: e.timestamp)

        prev_hash = None
        for entry in all_entries:
            payload = {
                "entity_type": entry.entity_type,
                "entity_id": str(entry.entity_id),
                "action": entry.action,
                "actor": entry.actor,
                "timestamp": entry.timestamp.isoformat(),
                "log_metadata": entry.log_metadata,
                "prev_hash": prev_hash,
            }
            expected_hash = hashlib.sha256(
                json.dumps(payload, sort_keys=True, default=str).encode()
            ).hexdigest()
            if expected_hash != entry.curr_hash:
                return False
            prev_hash = entry.curr_hash
        return True