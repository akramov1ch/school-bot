from __future__ import annotations

from sqlalchemy import select, delete
from sqlalchemy.orm import joinedload

from app.models.school import ClassSubject, Class
from app.repositories.base import BaseRepository


class ClassSubjectRepository(BaseRepository):
    """
    Sinf, Fan va O'qituvchi o'rtasidagi bog'liqliklar bilan ishlovchi repository.
    """

    async def teacher_has_class(self, emp_id: int, class_name: str) -> bool:
        """O'qituvchiga ma'lum bir sinf biriktirilganligini tekshirish"""
        q = (
            select(ClassSubject.id)
            .join(Class, Class.id == ClassSubject.class_id)
            .where(Class.class_name == class_name, ClassSubject.teacher_employee_id == emp_id)
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none() is not None

    async def list_for_teacher(self, teacher_employee_id: int) -> list[ClassSubject]:
        """
        O'qituvchiga biriktirilgan barcha fanlar va sinflar ro'yxatini olish.
        Sinf ma'lumotlarini (cls) ham qo'shib yuklaydi (joinedload).
        """
        q = (
            select(ClassSubject)
            .options(joinedload(ClassSubject.cls)) # Sinf ma'lumotlarini ham yuklash
            .where(ClassSubject.teacher_employee_id == teacher_employee_id)
            .where(ClassSubject.status == "active")
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def list_unique_classes_for_teacher(self, teacher_employee_id: int) -> list[str]:
        """
        O'qituvchi dars o'tadigan sinflarning faqat nomlarini (takrorlanmas) qaytaradi.
        Tugmalar yasash uchun juda qulay.
        """
        q = (
            select(Class.class_name)
            .join(ClassSubject, ClassSubject.class_id == Class.id)
            .where(ClassSubject.teacher_employee_id == teacher_employee_id)
            .distinct()
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def replace_for_class(self, class_id: int, items: list[tuple[str, int, str | None]]) -> None:
        """
        Google Sheets sinxronizatsiyasi paytida sinfga tegishli barcha fanlarni yangilash.
        Avval eskilarini o'chiradi, keyin yangilarini yozadi.
        items: [(subject_name, teacher_employee_id, status)]
        """
        # Eskilarini o'chirish
        await self.session.execute(
            delete(ClassSubject).where(ClassSubject.class_id == class_id)
        )
        
        # Yangilarini qo'shish
        for subject_name, teacher_id, status in items:
            cs = ClassSubject(
                class_id=class_id, 
                subject_name=subject_name, 
                teacher_employee_id=teacher_id, 
                status=status or "active"
            )
            self.session.add(cs)
        
        await self.session.flush()

    async def get_subject_for_teacher_and_class(self, teacher_id: int, class_id: int) -> str:
        """O'qituvchi ma'lum bir sinfda qaysi fandan dars o'tishini aniqlash"""
        q = (
            select(ClassSubject.subject_name)
            .where(
                ClassSubject.teacher_employee_id == teacher_id,
                ClassSubject.class_id == class_id
            )
            .limit(1)
        )
        res = await self.session.execute(q)
        return res.scalar_one_or_none() or "Fan"