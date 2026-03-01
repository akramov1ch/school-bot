from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update
from redis.asyncio import Redis

from app.core.cache import CacheKeys
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """
    Redis orqali foydalanuvchilarni xabar yuborish tezligini cheklash.
    """

    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_id = None
        
        # Update ichidan foydalanuvchi ID sini olish
        if isinstance(event, Update):
            if event.message:
                tg_id = event.message.from_user.id
            elif event.callback_query:
                tg_id = event.callback_query.from_user.id

        if tg_id is not None:
            key = CacheKeys.throttle_user(tg_id)
            # Redis-da hisoblagichni oshirish
            count = await self.redis.incr(key)
            if count == 1:
                # Birinchi xabarda 1 soniyalik TTL qo'yish
                await self.redis.expire(key, 1)

            # Agar limitdan oshsa, xabarni to'xtatish
            if count > self.settings.TG_THROTTLE_BURST:
                if isinstance(event, Update) and event.message:
                    await event.message.answer("⏳ Juda tez yuboryapsiz. Iltimos, biroz kuting.")
                return None

        return await handler(event, data)