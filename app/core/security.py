from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.timezone import now_tz


_ph = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8, hash_len=32, salt_len=16)


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(hash_value: str, plain: str) -> bool:
    try:
        return _ph.verify(hash_value, plain)
    except VerifyMismatchError:
        return False


@dataclass
class BruteForceState:
    fails: int
    blocked_until_ts: Optional[int]


def epoch_seconds_now() -> int:
    return int(now_tz().timestamp())