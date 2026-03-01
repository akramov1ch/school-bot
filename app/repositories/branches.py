from __future__ import annotations

from sqlalchemy import select

from app.models.faceid import Branch
from app.repositories.base import BaseRepository


class BranchRepository(BaseRepository):
    async def create(self, *, name: str, attendance_sheet_id: str) -> Branch:
        b = Branch(name=name, attendance_sheet_id=attendance_sheet_id)
        self.session.add(b)
        await self.session.flush()
        return b

    async def get_by_name(self, name: str) -> Branch | None:
        stmt = select(Branch).where(Branch.name == name)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_id(self, branch_id: int) -> Branch | None:
        stmt = select(Branch).where(Branch.id == branch_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list(self, limit: int = 100) -> list[Branch]:
        stmt = select(Branch).order_by(Branch.id.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())