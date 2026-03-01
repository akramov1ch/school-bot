from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.school import ParentStudent, Student, Class
from app.repositories.base import BaseRepository


@dataclass
class ParentStudentView:
    student_id: int
    student_uid: str
    full_name: str
    class_name: str


class ParentStudentRepository(BaseRepository):
    async def bind(self, parent_user_id: int, student_id: int) -> None:
        ps = ParentStudent(parent_user_id=parent_user_id, student_id=student_id)
        self.session.add(ps)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            # already bound: ignore
            return

    async def list_students_for_parent(self, parent_user_id: int) -> list[ParentStudentView]:
        q = (
            select(Student, Class)
            .join(ParentStudent, ParentStudent.student_id == Student.id)
            .join(Class, Class.id == Student.class_id)
            .where(ParentStudent.parent_user_id == parent_user_id)
            .order_by(Student.id.asc())
        )
        res = await self.session.execute(q)
        rows = res.all()
        out: list[ParentStudentView] = []
        for st, cls in rows:
            out.append(ParentStudentView(student_id=st.id, student_uid=st.student_uid, full_name=st.full_name, class_name=cls.class_name))
        return out

    async def list_parent_telegram_ids_for_student(self, student_id: int) -> list[int]:
        from app.models.school import User

        q = (
            select(User.telegram_id)
            .join(ParentStudent, ParentStudent.parent_user_id == User.id)
            .where(ParentStudent.student_id == student_id)
        )
        res = await self.session.execute(q)
        return [int(x) for x in res.scalars().all()]