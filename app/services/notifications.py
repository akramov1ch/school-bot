from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.timezone import now_tz, to_date_str
from app.repositories.parent_student import ParentStudentRepository
from app.repositories.grades import GradeRepository
from app.repositories.homeworks import HomeworkRepository
from app.repositories.payments import PaymentRepository
from app.repositories.complaints import ComplaintRepository

logger = get_logger(__name__)


class NotificationService:
    """
    Sends Telegram messages to users via Bot API HTTP calls.
    This keeps services decoupled from aiogram runtime context and works in background jobs too.
    """

    def __init__(self, session) -> None:
        self.session = session
        self.settings = Settings()

    async def _send(self, chat_id: int, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.settings.BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": text}
        timeout = httpx.Timeout(self.settings.TELEGRAM_NOTIFY_HTTP_TIMEOUT_SEC)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()

    async def notify_parents_grade(self, student_id: int, grade_id: int) -> None:
        ps_repo = ParentStudentRepository(self.session)
        tg_ids = await ps_repo.list_parent_telegram_ids_for_student(student_id)
        if not tg_ids:
            return

        g_repo = GradeRepository(self.session)
        grade = await g_repo.get_by_id(grade_id)
        if not grade:
            return

        comment = grade.comment or "-"
        teacher = grade.teacher.full_name if grade.teacher else "-"
        text = (
            "📊 Yangi baho qo‘shildi\n\n"
            f"👶 O‘quvchi: {grade.student.full_name} ({grade.cls.class_name})\n"
            f"📚 Fan: {grade.subject_name}\n"
            f"⭐ Ball: {grade.score}\n"
            f"📅 Sana: {grade.date}\n"
            f"📝 Izoh: {comment}\n"
            f"👨‍🏫 Ustoz: {teacher}"
        )

        for chat_id in tg_ids:
            try:
                await self._send(chat_id, text)
            except Exception:
                logger.exception("Failed to notify parent (grade)", extra={"chat_id": chat_id})

    async def notify_class_homework(self, class_id: int, homework_id: int) -> None:
        hw_repo = HomeworkRepository(self.session)
        hw = await hw_repo.get_by_id(homework_id)
        if not hw:
            return

        from app.models.school import ParentStudent, Student, User
        from sqlalchemy import select

        # parents of students in this class
        stmt = (
            select(User.telegram_id)
            .join(ParentStudent, ParentStudent.parent_user_id == User.id)
            .join(Student, Student.id == ParentStudent.student_id)
            .where(Student.class_id == class_id)
        )
        res = await self.session.execute(stmt)
        tg_ids = [int(x) for x in res.scalars().all()]
        tg_ids = list(dict.fromkeys(tg_ids))  # unique preserve order

        deadline = hw.deadline or "-"
        teacher = hw.teacher.full_name if hw.teacher else "-"
        # template asks per-student; for class broadcast we keep "O‘quvchi: {name} ({class})"
        # MVP: send without specific student name; use "-".
        text = (
            "✍️ Uyga vazifa berildi\n\n"
            f"👶 O‘quvchi: - ({hw.cls.class_name})\n"
            f"📚 Fan: {hw.subject_name}\n"
            f"📝 Vazifa: {hw.text}\n"
            f"⏳ Deadline: {deadline}\n"
            f"👨‍🏫 Ustoz: {teacher}"
        )
        for chat_id in tg_ids:
            try:
                await self._send(chat_id, text)
            except Exception:
                logger.exception("Failed to notify parent (homework)", extra={"chat_id": chat_id})

    async def notify_parents_payment(self, payment_id: int) -> None:
        pay_repo = PaymentRepository(self.session)
        payment = await pay_repo.get_by_id(payment_id)
        if not payment:
            return

        ps_repo = ParentStudentRepository(self.session)
        tg_ids = await ps_repo.list_parent_telegram_ids_for_student(payment.student_id)

        method = payment.method or "-"
        comment = payment.comment or "-"
        cashier = payment.cashier.full_name if payment.cashier else "-"

        text = (
            "💳 To‘lov qabul qilindi (Kvitansiya)\n\n"
            f"👶 O‘quvchi: {payment.student.full_name} ({payment.student.cls.class_name})\n"
            f"💰 Summa: {float(payment.amount)} {payment.currency}\n"
            f"🧾 To‘lov ID: {payment.payment_code}\n"
            f"💳 Usul: {method}\n"
            f"📝 Izoh: {comment}\n"
            f"📅 Sana: {payment.paid_at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"👨‍💼 Kassir: {cashier}"
        )

        for chat_id in tg_ids:
            try:
                await self._send(chat_id, text)
            except Exception:
                logger.exception("Failed to notify parent (payment)", extra={"chat_id": chat_id})

    async def notify_complaint(self, complaint_id: int) -> None:
        comp_repo = ComplaintRepository(self.session)
        comp = await comp_repo.get_by_id(complaint_id)
        if not comp:
            return

        if comp.target_type == "PARENT":
            ps_repo = ParentStudentRepository(self.session)
            tg_ids = await ps_repo.list_parent_telegram_ids_for_student(comp.student_id)
        else:
            # management/admins: notify all ADMIN users (simple)
            from app.models.school import User
            from sqlalchemy import select

            stmt = select(User.telegram_id).where(User.role == "ADMIN")
            res = await self.session.execute(stmt)
            tg_ids = [int(x) for x in res.scalars().all()]

        text = (
            "✉️ Shikoyat\n\n"
            f"👶 O‘quvchi: {comp.student.full_name} ({comp.student.cls.class_name})\n"
            f"👨‍🏫 Ustoz: {comp.teacher.full_name}\n"
            f"🎯 Target: {comp.target_type}\n"
            f"📝 Matn: {comp.text}\n"
            f"📅 Sana: {to_date_str(now_tz())}"
        )

        for chat_id in tg_ids:
            try:
                await self._send(chat_id, text)
            except Exception:
                logger.exception("Failed to notify complaint target", extra={"chat_id": chat_id})