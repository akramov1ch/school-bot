from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from redis.asyncio import Redis

from app.core.config import Settings
from app.core.logging import get_logger
from app.bot.middlewares.rbac import RBACMiddleware
from app.bot.middlewares.throttling import ThrottlingMiddleware
from app.bot.middlewares.audit import AuditMiddleware

from app.bot.routers.start import router as start_router
from app.bot.routers.auth_parent import router as auth_parent_router
from app.bot.routers.auth_employee import router as auth_employee_router
from app.bot.routers.parent import router as parent_router
from app.bot.routers.teacher import router as teacher_router
from app.bot.routers.cashier import router as cashier_router
from app.bot.routers.hr import router as hr_router
from app.bot.routers.admin import router as admin_router
from app.bot.routers.face_enroll import router as face_enroll_router

logger = get_logger(__name__)


def create_bot_and_dispatcher(settings: Settings, redis: Redis) -> tuple[Bot, Dispatcher]:
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Middlewares (outer)
    dp.update.outer_middleware(ThrottlingMiddleware(redis=redis, settings=settings))
    dp.update.outer_middleware(RBACMiddleware())
    dp.update.outer_middleware(AuditMiddleware())

    # Routers
    dp.include_router(start_router)
    dp.include_router(auth_parent_router)
    dp.include_router(auth_employee_router)
    dp.include_router(parent_router)
    dp.include_router(teacher_router)
    dp.include_router(cashier_router)
    dp.include_router(hr_router)
    dp.include_router(admin_router)
    dp.include_router(face_enroll_router)

    logger.info("Bot + Dispatcher created")
    return bot, dp