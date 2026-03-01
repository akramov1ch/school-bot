"""
Very lightweight smoke checks (not a full unit test suite).

Run locally:
  python -m tests.smoke_test

What it does:
- Loads Settings
- Imports core components
- Ensures Alembic metadata imports
"""
from __future__ import annotations

from app.core.config import Settings
from app.models.base import Base
from app import models  # noqa


def main() -> None:
    s = Settings()
    assert s.TZ == "Asia/Tashkent"
    assert s.BOT_TOKEN
    assert s.GOOGLE_SHEETS_SPREADSHEET_ID
    assert Base.metadata.tables is not None
    print("SMOKE OK")


if __name__ == "__main__":
    main()