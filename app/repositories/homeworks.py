from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select, desc

from app.models.school import Homework, Class
from app.repositories.base import BaseRepository


@dataclass
class HomeworkView:
    id: int
    class_name: str
    subject_name: str
    text: str
    deadline: str | None


class HomeworkRepository(BaseRepository):
    async def create(
        self,
        *,
        class_id: int,
        subject_name: str,
        teacher_employee_id: int,
        text: str,
        deadline: str | None,
        attachment_file_id: str | None,
    ) -> Homework:
        hw = Homework(
            class_id=class_id,
            subject_name=subject_name,
            teacher_employee_id=teacher_employee_id,
            text=text,
            deadline=deadline,
            attachment_file_id=attachment_file_id,
        )
        self.session.add(hw)
        await self.session.flush()
        return hw

    async def get_by_id(self, homework_id: int) -> Homework | None:
        q = select(Homework).where(Homework.id == homework_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def latest_for_parent(self, parent_user_id: int, limit: int = 20) -> list[HomeworkView]:
        from app.models.school import ParentStudent, Student

        q = (
            select(Homework, Class)
            .join(Class, Class.id == Homework.class_id)
            .join(Student, Student.class_id == Homework.class_id)
            .join(ParentStudent, ParentStudent.student_id == Student.id)
            .where(ParentStudent.parent_user_id == parent_user_id)
            .order_by(desc(Homework.id))
            .limit(limit)
        )
        res = await self.session.execute(q)
        rows = res.all()
        out: list[HomeworkView] = []
        for hw, cls in rows:
            out.append(HomeworkView(id=hw.id, class_name=cls.class_name, subject_name=hw.subject_name, text=hw.text, deadline=hw.deadline))
        return out