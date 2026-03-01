from __future__ import annotations

from sqlalchemy import select, desc

from app.models.sync import SyncLog
from app.repositories.base import BaseRepository


class SyncLogRepository(BaseRepository):
    async def create(self, *, type_: str, status: str, payload_json: str | None) -> SyncLog:
        s = SyncLog(type=type_, status=status, payload_json=payload_json)
        self.session.add(s)
        await self.session.flush()
        return s

    async def latest(self, limit: int = 50) -> list[SyncLog]:
        stmt = select(SyncLog).order_by(desc(SyncLog.id)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())