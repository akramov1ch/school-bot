from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select, desc

from app.models.school import Grade, Student, Class
from app.repositories.base import BaseRepository


@dataclass
class GradeView:
    id: int
    student_name: str
    class_name: str
    subject_name: str
    score: int
    date: str


class GradeRepository(BaseRepository):
    async def create(
        self,
        *,
        student_id: int,
        class_id: int,
        subject_name: str,
        teacher_employee_id: int | None,
        score: int,
        date_: str,
        comment: str | None,
    ) -> Grade:
        g = Grade(
            student_id=student_id,
            class_id=class_id,
            subject_name=subject_name,
            teacher_employee_id=teacher_employee_id,
            score=score,
            date=date_,
            comment=comment or None,
        )
        self.session.add(g)
        await self.session.flush()
        return g

    async def get_by_id(self, grade_id: int) -> Grade | None:
        q = select(Grade).where(Grade.id == grade_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def latest_for_parent(self, parent_user_id: int, limit: int = 20) -> list[GradeView]:
        from app.models.school import ParentStudent

        q = (
            select(Grade, Student, Class)
            .join(Student, Student.id == Grade.student_id)
            .join(Class, Class.id == Grade.class_id)
            .join(ParentStudent, ParentStudent.student_id == Student.id)
            .where(ParentStudent.parent_user_id == parent_user_id)
            .order_by(desc(Grade.id))
            .limit(limit)
        )
        res = await self.session.execute(q)
        rows = res.all()
        out: list[GradeView] = []
        for g, st, cls in rows:
            out.append(GradeView(id=g.id, student_name=st.full_name, class_name=cls.class_name, subject_name=g.subject_name, score=g.score, date=g.date))
        return out