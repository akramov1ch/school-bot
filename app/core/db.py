from __future__ import annotations

from typing import AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: Optional[AsyncEngine] = None
_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


async def init_db(settings: Settings) -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        return

    # NullPool is safer for containers with many forks; can switch to default pool in prod if desired.
    _engine = create_async_engine(settings.DATABASE_DSN, echo=False, poolclass=NullPool)
    _sessionmaker = async_sessionmaker(bind=_engine, expire_on_commit=False)

    logger.info("Database initialized")


def get_engine() -> AsyncEngine:
    if _engine is None:
        raise RuntimeError("DB engine not initialized")
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        raise RuntimeError("DB sessionmaker not initialized")
    return _sessionmaker


async def session_scope() -> AsyncIterator[AsyncSession]:
    sm = get_sessionmaker()
    async with sm() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise