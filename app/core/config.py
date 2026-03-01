from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    ENV: Literal["local", "dev", "prod"] = "local"
    LOG_LEVEL: str = "INFO"

    # Timezone
    TZ: str = "Asia/Tashkent"

    # Telegram
    BOT_TOKEN: str = Field(..., description="Telegram bot token")

    # Postgres
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "school"
    POSTGRES_USER: str = "school"
    POSTGRES_PASSWORD: str = "school"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # FastAPI
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Google Sheets
    GOOGLE_SERVICE_ACCOUNT_JSON: str = "google_creds/service_account.json"
    GOOGLE_SHEETS_SPREADSHEET_ID: str = Field(..., description="Master spreadsheet with students/employees/etc tabs")

    # Attendance: sheet_id stored per branch in DB, but these are defaults/optional
    ATTENDANCE_DEFAULT_HEADERS: str = "Sana,Vaqt,Xodim,FX,Holat"

    # Scheduler
    SHEETS_SYNC_CRON_MINUTE: int = 0  # every hour at :00
    PAYMENTS_RETRY_INTERVAL_SEC: int = 60

    # Security
    PASSWORD_MIN_LEN: int = 10
    PASSWORD_MAX_LEN: int = 12
    BRUTE_FORCE_MAX_FAILS: int = 5
    BRUTE_FORCE_BLOCK_MINUTES: int = 10

    # Throttling
    TG_THROTTLE_RATE_PER_SEC: float = 1.0  # per user
    TG_THROTTLE_BURST: int = 3

    # Hikvision
    HIK_EVENT_DUP_TTL_SEC: int = 45
    HIK_HTTP_TIMEOUT_SEC: float = 8.0
    TELEGRAM_NOTIFY_HTTP_TIMEOUT_SEC: float = 6.0

    @property
    def DATABASE_DSN(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_DSN(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def google_service_account_path(self) -> Path:
        return Path(self.GOOGLE_SERVICE_ACCOUNT_JSON).expanduser().resolve()