#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio

from app.core.config import Settings
from app.core.db import init_db, get_sessionmaker
from app.repositories.users import UserRepository
from app.models.enums import UserRole


async def main() -> None:
    settings = Settings()
    await init_db(settings)

    parser = argparse.ArgumentParser("create_admin.py")
    parser.add_argument("--telegram-id", type=int, required=True)
    parser.add_argument("--full-name", type=str, default="Admin")
    args = parser.parse_args()

    async with get_sessionmaker()() as session:
        repo = UserRepository(session)
        u = await repo.get_by_telegram_id(args.telegram_id)
        if u:
            u.role = UserRole.ADMIN.value
            u.full_name = args.full_name or u.full_name
            session.add(u)
        else:
            from app.models.school import User

            u = User(telegram_id=args.telegram_id, full_name=args.full_name, role=UserRole.ADMIN.value)
            session.add(u)
        await session.commit()

    print("ADMIN READY:", args.telegram_id)


if __name__ == "__main__":
    asyncio.run(main())