from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.school import User
from app.models.enums import UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        q = select(User).where(User.telegram_id == telegram_id)
        res = await self.session.execute(q)
        return res.scalar_one_or_none()

    async def get_or_create_parent(self, telegram_id: int, full_name: str) -> User:
        u = await self.get_by_telegram_id(telegram_id)
        if u:
            # if user existed as guest, promote to PARENT
            if u.role == UserRole.GUEST:
                u.role = UserRole.PARENT
                u.full_name = full_name or u.full_name
                self.session.add(u)
            return u
        u = User(telegram_id=telegram_id, full_name=full_name, role=UserRole.PARENT.value)
        self.session.add(u)
        await self.session.flush()
        return u

    async def bind_employee_user(self, telegram_id: int, full_name: str, employee_id: int, role: str) -> User:
        u = await self.get_by_telegram_id(telegram_id)
        if u:
            u.full_name = full_name or u.full_name
            u.employee_id = employee_id
            u.role = role
            self.session.add(u)
            return u
        u = User(telegram_id=telegram_id, full_name=full_name, employee_id=employee_id, role=role)
        self.session.add(u)
        await self.session.flush()
        return u

    async def get_or_create_guest(self, telegram_id: int, full_name: str = "") -> User:
        u = await self.get_by_telegram_id(telegram_id)
        if u:
            if full_name and not u.full_name:
                u.full_name = full_name
                self.session.add(u)
            return u
        u = User(telegram_id=telegram_id, full_name=full_name, role=UserRole.GUEST.value)
        self.session.add(u)
        await self.session.flush()
        return u

    async def set_lang(self, telegram_id: int, lang: str) -> User:
        u = await self.get_by_telegram_id(telegram_id)
        if not u:
            u = User(telegram_id=telegram_id, full_name='', role=UserRole.GUEST.value, lang=lang)
            self.session.add(u)
            await self.session.flush()
            return u
        u.lang = lang
        self.session.add(u)
        return u
