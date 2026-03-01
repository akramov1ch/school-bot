from __future__ import annotations

from sqlalchemy import select

from app.models.school import Class
from app.repositories.base import BaseRepository


class ClassRepository(BaseRepository):
    async def get_by_name(self, class_name: str) -> Class | None:
        q = select(Class).where(Class.class_name == class_name)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def upsert(self, class_name: str, status: str) -> Class:
        existing = await self.get_by_name(class_name)
        if existing:
            existing.status = status
            self.session.add(existing)
            return existing
        cls = Class(class_name=class_name, status=status)
        self.session.add(cls)
        await self.session.flush()
        return cls

    async def list(self, limit: int = 200) -> list[Class]:
        q = select(Class).order_by(Class.class_name.asc()).limit(limit)
        res = await self.session.execute(q)
        return list(res.scalars().all())