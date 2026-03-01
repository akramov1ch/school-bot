from __future__ import annotations

from sqlalchemy import select, desc

from app.models.school import Feedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository):
    async def create(self, *, from_parent_user_id: int, type_: str, text: str) -> Feedback:
        fb = Feedback(from_parent_user_id=from_parent_user_id, type=type_, text=text, is_seen_by_admin=False)
        self.session.add(fb)
        await self.session.flush()
        return fb

    async def list_unseen(self, limit: int = 20) -> list[Feedback]:
        stmt = select(Feedback).where(Feedback.is_seen_by_admin.is_(False)).order_by(desc(Feedback.id)).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())