from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update

from app.core.db import get_sessionmaker
from app.core.logging import get_logger
from app.core.utils import dumps_json

logger = get_logger(__name__)


class AuditMiddleware(BaseMiddleware):
    """
    Botdagi asosiy harakatlarni audit log sifatida bazaga yozish.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Avval handler ishlasin (xabarga javob qaytarilsin)
        result = await handler(event, data)

        # RBACMiddleware tomonidan qo'shilgan foydalanuvchi ma'lumotini olish
        actor = data.get("actor_user")
        actor_id = getattr(actor, "id", None)

        action = None
        payload = {}

        # Update ichidan amal turini va ma'lumotlarni ajratish
        if isinstance(event, Update):
            if event.message:
                action = "message"
                payload = {
                    "text": event.message.text,
                    "chat_id": event.message.chat.id,
                }
            elif event.callback_query:
                action = "callback"
                payload = {
                    "data": event.callback_query.data,
                    "chat_id": event.callback_query.message.chat.id if event.callback_query.message else None,
                }

        # Agar amal aniqlangan bo'lsa, bazaga yozish
        if action:
            try:
                async with get_sessionmaker()() as session:
                    from app.repositories.audit_logs import AuditLogRepository

                    repo = AuditLogRepository(session)
                    await repo.create(
                        actor_user_id=actor_id, 
                        action=action, 
                        payload_json=dumps_json(payload)
                    )
                    await session.commit()
            except Exception:
                logger.exception("Audit log write failed")

        return result