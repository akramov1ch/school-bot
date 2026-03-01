#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import sys

from app.core.config import Settings
from app.core.db import init_db, get_sessionmaker
from app.core.redis import init_redis
from app.services.sync_sheets import SheetsSyncService
from app.services.payment_writer import PaymentSheetWriter


async def cmd_sync() -> None:
    async with get_sessionmaker()() as session:
        svc = SheetsSyncService(session=session)
        res = await svc.sync_all()
        await session.commit()
    print("SYNC RESULT:", res)


async def cmd_retry_payments() -> None:
    async with get_sessionmaker()() as session:
        w = PaymentSheetWriter(session=session)
        n = await w.retry_failed(limit=50)
        await session.commit()
    print("RETRIED:", n)


async def main() -> None:
    Settings()  # load env
    await init_db(Settings())

    parser = argparse.ArgumentParser("manage.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync", help="Run Google Sheets sync now")
    sub.add_parser("retry_payments", help="Retry failed payment sheet writes")

    args = parser.parse_args()

    if args.cmd == "sync":
        await cmd_sync()
    elif args.cmd == "retry_payments":
        await cmd_retry_payments()
    else:
        print("Unknown command")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())