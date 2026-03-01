from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Tashkent")


def now_tz() -> datetime:
    return datetime.now(tz=TZ)


def to_date_str(dt: datetime) -> str:
    # YYYY-MM-DD
    return dt.astimezone(TZ).date().isoformat()


def to_time_str(dt: datetime) -> str:
    # HH:MM:SS
    return dt.astimezone(TZ).time().strftime("%H:%M:%S")


def to_ddmmyyyy(dt: datetime) -> str:
    d = dt.astimezone(TZ).date()
    return d.strftime("%d.%m.%Y")