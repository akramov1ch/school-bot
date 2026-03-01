from __future__ import annotations

from sqlalchemy import select

from app.models.school import Complaint
from app.repositories.base import BaseRepository


class ComplaintRepository(BaseRepository):
    async def create(self, *, from_teacher_employee_id: int, student_id: int, target_type: str, text: str) -> Complaint:
        c = Complaint(from_teacher_employee_id=from_teacher_employee_id, student_id=student_id, target_type=target_type, text=text)
        self.session.add(c)
        await self.session.flush()
        return c

    async def get_by_id(self, complaint_id: int) -> Complaint | None:
        stmt = select(Complaint).where(Complaint.id == complaint_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()