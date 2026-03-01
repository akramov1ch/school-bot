from __future__ import annotations

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def init_redis(settings: Settings) -> Redis:
    client = Redis.from_url(settings.REDIS_DSN, decode_responses=True)
    # ping to ensure connectivity
    await client.ping()
    logger.info("Redis initialized")
    return client