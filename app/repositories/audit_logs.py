from __future__ import annotations

from sqlalchemy import select, desc

from app.models.audit import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository):
    async def create(self, *, actor_user_id: int | None, action: str, payload_json: str | None) -> AuditLog:
        a = AuditLog(actor_user_id=actor_user_id, action=action, payload_json=payload_json)
        self.session.add(a)
        await self.session.flush()
        return a

    async def latest(self, limit: int = 50) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(desc(AuditLog.id)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())