from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, desc, or_

from app.core.timezone import now_tz
from app.models.school import Payment, Student, Class
from app.repositories.base import BaseRepository


@dataclass
class PaymentView:
    id: int
    payment_code: str
    student_name: str
    amount: float
    currency: str
    paid_at: datetime


class PaymentRepository(BaseRepository):
    async def _next_payment_code(self) -> str:
        dt = now_tz()
        year = dt.year
        # naive sequence: count payments this year + 1 (OK for MVP; in prod use DB sequence)
        q = select(Payment.id).where(Payment.payment_code.like(f"PAY-{year}-%"))
        res = await self.session.execute(q)
        n = len(res.scalars().all()) + 1
        return f"PAY-{year}-{n:06d}"

    async def create_payment(
        self,
        *,
        student_id: int,
        amount: float,
        currency: str,
        method: str | None,
        comment: str | None,
        cashier_employee_id: int | None,
    ) -> Payment:
        code = await self._next_payment_code()
        p = Payment(
            payment_code=code,
            student_id=student_id,
            amount=amount,
            currency=currency,
            method=method,
            comment=comment,
            cashier_employee_id=cashier_employee_id,
            paid_at=now_tz(),
            sheet_write_status="PENDING",
        )
        self.session.add(p)
        await self.session.flush()
        return p

    async def get_by_id(self, payment_id: int) -> Payment | None:
        q = select(Payment).where(Payment.id == payment_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def mark_sheet_status(self, payment_id: int, status: str) -> None:
        p = await self.get_by_id(payment_id)
        if not p:
            return
        p.sheet_write_status = status
        self.session.add(p)

    async def latest_for_parent(self, parent_user_id: int, limit: int = 20) -> list[PaymentView]:
        from app.models.school import ParentStudent

        q = (
            select(Payment, Student)
            .join(Student, Student.id == Payment.student_id)
            .join(ParentStudent, ParentStudent.student_id == Student.id)
            .where(ParentStudent.parent_user_id == parent_user_id)
            .order_by(desc(Payment.id))
            .limit(limit)
        )
        res = await self.session.execute(q)
        rows = res.all()
        out: list[PaymentView] = []
        for p, st in rows:
            out.append(
                PaymentView(
                    id=p.id,
                    payment_code=p.payment_code,
                    student_name=st.full_name,
                    amount=float(p.amount),
                    currency=p.currency,
                    paid_at=p.paid_at,
                )
            )
        return out

    async def search(self, q: str, limit: int = 20) -> list[PaymentView]:
        q = q.strip()
        if not q:
            return []
        stmt = (
            select(Payment, Student)
            .join(Student, Student.id == Payment.student_id)
            .where(or_(Payment.payment_code.ilike(f"%{q}%"), Student.student_uid.ilike(f"%{q}%")))
            .order_by(desc(Payment.id))
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        rows = res.all()
        out: list[PaymentView] = []
        for p, st in rows:
            out.append(PaymentView(id=p.id, payment_code=p.payment_code, student_name=st.full_name, amount=float(p.amount), currency=p.currency, paid_at=p.paid_at))
        return out

    async def list_failed_sheet_writes(self, limit: int = 50) -> list[Payment]:
        stmt = select(Payment).where(Payment.sheet_write_status == "FAILED").order_by(Payment.id.asc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())