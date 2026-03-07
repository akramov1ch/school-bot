from __future__ import annotations

from sqlalchemy import select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import Employee
from app.repositories.base import BaseRepository


class EmployeeRepository(BaseRepository):
    async def get_by_employee_uid(self, employee_uid: str) -> Employee | None:
        q = select(Employee).where(Employee.employee_uid == employee_uid)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_by_external_key(self, external_key: str) -> Employee | None:
        q = select(Employee).where(Employee.external_key == external_key)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_by_id(self, emp_id: int) -> Employee | None:
        q = select(Employee).where(Employee.id == emp_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def list(self, limit: int = 50) -> list[Employee]:
        q = select(Employee).order_by(Employee.full_name.asc()).limit(limit)
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def search(self, query: str, limit: int = 20) -> list[Employee]:
        q = (
            select(Employee)
            .where(or_(Employee.full_name.ilike(f"%{query}%"), Employee.employee_uid.ilike(f"%{query}%")))
            .order_by(Employee.full_name.asc())
            .limit(limit)
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())

    async def upsert_from_sheet(
        self,
        *,
        external_key: str | None,
        employee_uid: str,
        password_hash: str,
        full_name: str,
        role: str,
        subject: str | None,
        status: str,
        branch_id: int | None,
        phone: str | None,
    ) -> Employee:
        existing = None
        if external_key:
            existing = await self.get_by_external_key(external_key)
        if not existing:
            existing = await self.get_by_employee_uid(employee_uid)

        if existing:
            existing.external_key = external_key
            existing.employee_uid = employee_uid
            existing.full_name = full_name
            existing.role = role
            existing.subject = subject
            existing.status = status
            existing.branch_id = branch_id
            existing.phone = phone
            if password_hash:
                existing.password_hash = password_hash
            self.session.add(existing)
            return existing

        emp = Employee(
            external_key=external_key,
            employee_uid=employee_uid,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            subject=subject,
            status=status,
            branch_id=branch_id,
            phone=phone,
        )
        self.session.add(emp)
        await self.session.flush()
        return emp

    async def set_status_by_uid(self, employee_uid: str, status: str) -> bool:
        emp = await self.get_by_employee_uid(employee_uid)
        if not emp:
            return False
        emp.status = status
        self.session.add(emp)
        return True

    async def set_password_hash(self, employee_uid: str, password_hash: str) -> bool:
        emp = await self.get_by_employee_uid(employee_uid)
        if not emp:
            return False
        emp.password_hash = password_hash
        self.session.add(emp)
        return True

    async def set_notification_chat(self, employee_uid: str, chat_id: int) -> bool:
        emp = await self.get_by_employee_uid(employee_uid)
        if not emp:
            return False
        emp.notification_chat_id = chat_id
        self.session.add(emp)
        return True