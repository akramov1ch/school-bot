import asyncio

import uvicorn

from app.core.config import Settings
from app.core.hik_server import create_fastapi_app
from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_api_server(settings: Settings) -> None:
    app = create_fastapi_app(settings)

    config = uvicorn.Config(
        app=app,
        host=settings.API_HOST,
        port=settings.API_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    logger.info("Starting FastAPI server...", extra={"host": settings.API_HOST, "port": settings.API_PORT})
    # uvicorn Server.serve() is async
    await server.serve()