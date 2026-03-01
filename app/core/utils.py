from __future__ import annotations

import random
import re
import secrets
import string
from dataclasses import dataclass
from typing import Any, Optional

import orjson


STUDENT_UID_RE = re.compile(r"^FM\d{5}$")
EMPLOYEE_UID_RE = re.compile(r"^FX\d{5}$")


def is_student_uid(value: str) -> bool:
    return bool(STUDENT_UID_RE.match(value.strip().upper()))


def is_employee_uid(value: str) -> bool:
    return bool(EMPLOYEE_UID_RE.match(value.strip().upper()))


def normalize_uid(value: str) -> str:
    return value.strip().upper()


def gen_uid(prefix: str) -> str:
    """
    5 xonali random unique-candidate UID generator.
    Unikallikni DB UNIQUE constraint + retry kafolatlaydi.
    Misol: gen_uid("FM") -> "FM81247"
           gen_uid("FX") -> "FX10432"
    """
    p = (prefix or "").strip().upper()
    if not p:
        raise ValueError("prefix bo'sh bo'lmasligi kerak")

    # 5 xonali: 10000..99999 (90,000 kombinatsiya)
    n = secrets.randbelow(90000) + 10000
    return f"{p}{n}"


def gen_student_uid() -> str:
    return gen_uid("FM")


def gen_employee_uid() -> str:
    return gen_uid("FX")


def gen_password(min_len: int = 10, max_len: int = 12) -> str:
    n = random.randint(min_len, max_len)
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))


def dumps_json(data: Any) -> str:
    return orjson.dumps(data).decode("utf-8")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


@dataclass(frozen=True)
class RetryResult:
    ok: bool
    error: Optional[str] = None
    attempts: int = 0