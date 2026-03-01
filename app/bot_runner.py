import asyncio

from aiogram import Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from app.bot.bot import create_bot_and_dispatcher
from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_bot_polling(settings: Settings, redis: Redis) -> None:
    bot, dp = create_bot_and_dispatcher(settings=settings, redis=redis)

    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


def create_redis_fsm_storage(settings: Settings) -> RedisStorage:
    # aiogram's RedisStorage expects an aioredis client from redis.asyncio
    return RedisStorage.from_url(settings.REDIS_DSN)