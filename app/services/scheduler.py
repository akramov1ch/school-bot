from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.db import get_sessionmaker

logger = get_logger(__name__)


def start_scheduler(settings: Settings, redis) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.TZ)

    # IMPORTANT: pass coroutine directly, NOT lambda/create_task
    scheduler.add_job(
        _job_sheets_sync,
        trigger="cron",
        minute=settings.SHEETS_SYNC_CRON_MINUTE,
        id="sheets_sync_hourly",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    scheduler.add_job(
        _job_retry_failed_payments,
        trigger="interval",
        seconds=settings.PAYMENTS_RETRY_INTERVAL_SEC,
        id="payments_retry",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    scheduler.start()
    logger.info("Scheduler started")
    return scheduler


async def _job_sheets_sync() -> None:
    from app.services.sync_sheets import SheetsSyncService

    try:
        async with get_sessionmaker()() as session:
            svc = SheetsSyncService(session=session)
            res = await svc.sync_all()
            await session.commit()
        logger.info("Sheets sync OK", extra={"result": res})
    except Exception:
        logger.exception("Sheets sync FAILED")


async def _job_retry_failed_payments() -> None:
    from app.services.payment_writer import PaymentSheetWriter

    try:
        async with get_sessionmaker()() as session:
            writer = PaymentSheetWriter(session=session)
            n = await writer.retry_failed(limit=20)
            await session.commit()
        if n:
            logger.info("Payment retry processed", extra={"count": n})
    except Exception:
        logger.exception("Payment retry FAILED")