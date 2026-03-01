#!/usr/bin/env bash
set -e

echo "[entrypoint] Starting app (bot + api)..."

export PYTHONPATH=/app

echo "[entrypoint] Running migrations..."
alembic upgrade head

echo "[entrypoint] Launching..."
python -m main