from __future__ import annotations

from typing import Optional

from redis.asyncio import Redis

from app.core.config import Settings
from app.core.security import epoch_seconds_now
from app.core.logging import get_logger

logger = get_logger(__name__)


class CacheKeys:
    @staticmethod
    def brute_block(prefix: str, uid: str) -> str:
        # prefix: "student" or "employee"
        return f"bf:block:{prefix}:{uid}"

    @staticmethod
    def brute_fails(prefix: str, uid: str) -> str:
        return f"bf:fails:{prefix}:{uid}"

    @staticmethod
    def hik_dup(device_ip: str, employee_uid: str, action: str) -> str:
        return f"hik:dup:{device_ip}:{employee_uid}:{action}"

    @staticmethod
    def throttle_user(telegram_id: int) -> str:
        return f"throttle:tg:{telegram_id}"


class BruteForceProtector:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def is_blocked(self, prefix: str, uid: str) -> bool:
        key = CacheKeys.brute_block(prefix, uid)
        ttl = await self.redis.ttl(key)
        return ttl is not None and ttl > 0

    async def register_failure(self, prefix: str, uid: str) -> None:
        fails_key = CacheKeys.brute_fails(prefix, uid)
        fails = await self.redis.incr(fails_key)
        # keep fails counter a bit longer than block window
        await self.redis.expire(fails_key, (self.settings.BRUTE_FORCE_BLOCK_MINUTES * 60) + 60)

        if fails >= self.settings.BRUTE_FORCE_MAX_FAILS:
            block_key = CacheKeys.brute_block(prefix, uid)
            await self.redis.set(block_key, str(epoch_seconds_now()), ex=self.settings.BRUTE_FORCE_BLOCK_MINUTES * 60)
            logger.warning("Brute-force block activated", extra={"prefix": prefix, "uid": uid, "fails": fails})

    async def clear_failures(self, prefix: str, uid: str) -> None:
        await self.redis.delete(CacheKeys.brute_fails(prefix, uid))
        await self.redis.delete(CacheKeys.brute_block(prefix, uid))


class HikDuplicateGuard:
    def __init__(self, redis: Redis, settings: Settings) -> None:
        self.redis = redis
        self.settings = settings

    async def seen_recently(self, device_ip: str, employee_uid: str, action: str) -> bool:
        key = CacheKeys.hik_dup(device_ip, employee_uid, action)
        # SET NX with TTL
        ok = await self.redis.set(key, "1", nx=True, ex=self.settings.HIK_EVENT_DUP_TTL_SEC)
        return ok is None  # if None => already existed