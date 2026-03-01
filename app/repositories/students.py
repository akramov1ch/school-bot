from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import Student, Class
from app.repositories.base import BaseRepository


class StudentRepository(BaseRepository):
    async def get_by_student_uid(self, student_uid: str) -> Student | None:
        q = select(Student).where(Student.student_uid == student_uid)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_by_external_key(self, external_key: str) -> Student | None:
        q = select(Student).where(Student.external_key == external_key)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def upsert_from_sheet(
        self,
        *,
        external_key: str,
        student_uid: str,
        password_hash: str,
        full_name: str,
        class_id: int,
        status: str,
        notes: str | None,
    ) -> Student:
        existing = await self.get_by_external_key(external_key)
        if existing:
            existing.student_uid = student_uid
            existing.full_name = full_name
            existing.class_id = class_id
            existing.status = status
            existing.notes = notes
            # only set password_hash if provided (sync may keep existing)
            if password_hash:
                existing.password_hash = password_hash
            self.session.add(existing)
            return existing

        st = Student(
            external_key=external_key,
            student_uid=student_uid,
            password_hash=password_hash,
            full_name=full_name,
            class_id=class_id,
            status=status,
            notes=notes,
        )
        self.session.add(st)
        await self.session.flush()
        return st

    async def list_by_class(self, class_id: int, limit: int = 200) -> list[Student]:
        q = select(Student).where(Student.class_id == class_id).limit(limit)
        res = await self.session.execute(q)
        return list(res.scalars().all())