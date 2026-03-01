import asyncio

from app.core.config import Settings
from app.core.logging import setup_logging, get_logger
from app.core.db import init_db
from app.core.redis import init_redis
from app.bot_runner import run_bot_polling
from app.api_runner import run_api_server
from app.services.scheduler import start_scheduler

logger = get_logger(__name__)


async def main() -> None:
    settings = Settings()  # loads env
    setup_logging(settings.LOG_LEVEL)

    logger.info("Booting application", extra={"env": settings.ENV})

    await init_db(settings)
    redis = await init_redis(settings)

    # Start APScheduler in-process (jobs: hourly sheets sync, payments retry, etc.)
    scheduler = start_scheduler(settings=settings, redis=redis)

    # Run bot polling + FastAPI server concurrently in same container/process.
    # If you prefer separate services, README shows how to run them separately.
    bot_task = asyncio.create_task(run_bot_polling(settings=settings, redis=redis), name="bot_polling")
    api_task = asyncio.create_task(run_api_server(settings=settings), name="api_server")

    done, pending = await asyncio.wait({bot_task, api_task}, return_when=asyncio.FIRST_EXCEPTION)

    for t in done:
        exc = t.exception()
        if exc:
            logger.exception("A main task crashed", exc_info=exc)

    for t in pending:
        t.cancel()

    scheduler.shutdown(wait=False)
    await redis.close()


if __name__ == "__main__":
    asyncio.run(main())