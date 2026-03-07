from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent

@lru_cache(maxsize=4)
def _load(lang: str) -> dict[str, Any]:
    path = BASE_DIR / f"{lang}.json"
    if not path.exists():
        path = BASE_DIR / "uz.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, lang: str = "uz", **kwargs: Any) -> str:
    data = _load(lang)
    template = data.get(key) or _load("uz").get(key) or key
    try:
        return str(template).format(**kwargs)
    except Exception:
        return str(template)
