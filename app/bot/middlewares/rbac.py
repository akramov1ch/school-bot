from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.core.db import get_sessionmaker
from app.models.enums import UserRole


class RBACMiddleware(BaseMiddleware):
    """
    Injects `actor_user` (DB user) and `actor_role` into handler data.
    
    Ushbu middleware Update darajasida ishlaydi va har bir xabar yuborgan 
    foydalanuvchini bazadan tekshirib, uning rolini aniqlaydi.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user = None

        # Middleware Update darajasida bo'lgani uchun event Update obyektidir.
        # Update ichidan message yoki callback_query orqali foydalanuvchini olamiz.
        if isinstance(event, Update):
            if event.message:
                tg_user = event.message.from_user
            elif event.callback_query:
                tg_user = event.callback_query.from_user
            elif event.edited_message:
                tg_user = event.edited_message.from_user

        role: UserRole = UserRole.GUEST
        db_user = None

        if tg_user:
            telegram_id = int(tg_user.id)
            # Ma'lumotlar bazasidan foydalanuvchini qidirish
            async with get_sessionmaker()() as session:
                from app.repositories.users import UserRepository

                repo = UserRepository(session)
                db_user = await repo.get_by_telegram_id(telegram_id)
                
                if db_user:
                    # Agar foydalanuvchi bazada bo'lsa, uning rolini olamiz
                    role = db_user.role

        # Handlerlarga (routerlarga) ma'lumotlarni uzatish
        data["actor_user"] = db_user
        data["actor_role"] = role
        
        return await handler(event, data)