from __future__ import annotations

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    # clear existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)

    # quiet noisy libs
    logging.getLogger("uvicorn.error").setLevel(level.upper())
    logging.getLogger("uvicorn.access").setLevel(level.upper())
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("googleapiclient.discovery_cache").setLevel("ERROR")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return logging.getLogger(name or "app")