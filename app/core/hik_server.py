from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import httpx
from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis

from app.core.cache import HikDuplicateGuard
from app.core.config import Settings
from app.core.logging import get_logger
from app.core.sheets import GoogleSheetManager
from app.core.timezone import now_tz, to_date_str, to_time_str

# Repos/services are imported lazily inside functions to avoid circular imports.

logger = get_logger(__name__)


def create_fastapi_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="School Hikvision Attendance API", default_response_class=ORJSONResponse)

    # ---- Startup / Shutdown lifecycle ----

    @app.on_event("startup")
    async def _startup() -> None:
        # DB init (important if API runs standalone)
        from app.core.db import init_db
        from app.core.redis import init_redis

        await init_db(settings)

        # Redis init once, then reuse
        redis = await init_redis(settings)
        app.state.redis = redis
        app.state.settings = settings

        logger.info("FastAPI lifecycle initialized")

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        redis: Optional[Redis] = getattr(app.state, "redis", None)
        if redis is not None:
            try:
                await redis.close()
            except Exception:
                logger.exception("Failed to close redis on shutdown")

    # ---- Routes ----

    @app.get("/health")
    async def health() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/hikvision/event")
    async def hik_event(request: Request, background: BackgroundTasks) -> Dict[str, Any]:
        """
        Accepts Hikvision event payloads.
        We expect JSON; if multipart, we attempt to parse form fields.

        We extract:
        - device IP: request.client.host OR header X-Device-IP
        - employee_id (FXxxxxx): from payload fields
        - subEventType / eventType: used for action mapping
        """
        device_ip = request.headers.get("X-Device-IP") or (request.client.host if request.client else "unknown")

        content_type = request.headers.get("content-type", "")
        payload: Dict[str, Any] = {}
        if "application/json" in content_type:
            payload = await request.json()
        else:
            form = await request.form()
            payload = dict(form)

        redis: Redis = request.app.state.redis  # startup'da yaratilgan, reuse
        background.add_task(process_hik_event, settings, redis, device_ip, payload)
        return {"ok": True}

    return app


async def process_hik_event(settings: Settings, redis: Redis, device_ip: str, payload: Dict[str, Any]) -> None:
    from app.repositories.devices import DeviceRepository
    from app.repositories.employees import EmployeeRepository
    from app.repositories.branches import BranchRepository
    from app.core.db import get_sessionmaker

    dup_guard = HikDuplicateGuard(redis, settings)

    employee_uid = _extract_employee_uid(payload)
    if not employee_uid:
        logger.warning("Hik event missing employee uid", extra={"device_ip": device_ip})
        return

    async with get_sessionmaker()() as session:
        device_repo = DeviceRepository(session)
        employee_repo = EmployeeRepository(session)
        branch_repo = BranchRepository(session)

        device = await device_repo.get_by_ip(device_ip)
        if not device:
            logger.warning("Unknown Hik device", extra={"device_ip": device_ip})
            return

        employee = await employee_repo.get_by_employee_uid(employee_uid)
        if not employee:
            logger.warning("Unknown employee", extra={"employee_uid": employee_uid, "device_ip": device_ip})
            return

        branch = await branch_repo.get_by_id(device.branch_id)
        if not branch:
            logger.warning("Branch not found for device", extra={"device_ip": device_ip})
            return

        action = _action_from_device(device.device_type, payload)
        if await dup_guard.seen_recently(device_ip, employee_uid, action):
            logger.info(
                "Duplicate attendance skipped",
                extra={"device_ip": device_ip, "employee_uid": employee_uid, "action": action},
            )
            return

        # ---- Google Sheets: BLOCKING -> to_thread ----
        sheets = GoogleSheetManager(settings)
        res = await asyncio.to_thread(
            sheets.log_attendance,
            spreadsheet_id=branch.attendance_sheet_id,
            employee_name=employee.full_name,
            employee_id=employee.employee_uid,
            action=action,
        )
        if not res.ok:
            logger.error("Attendance sheet write failed", extra={"error": res.error, "branch": branch.name})

        # Notify telegram (if employee.notification_chat_id set)
        if employee.notification_chat_id:
            await _send_telegram_attendance(
                settings=settings,
                chat_id=employee.notification_chat_id,
                employee_name=employee.full_name,
                employee_id=employee.employee_uid,
                branch_name=branch.name,
                action=action,
            )


def _extract_employee_uid(payload: Dict[str, Any]) -> Optional[str]:
    # Common possible keys
    for key in ("employeeNoString", "employeeNo", "personId", "employee_id", "employeeUid"):
        v = payload.get(key)
        if v:
            s = str(v).strip().upper()
            if s.startswith("FX") and len(s) == 7:
                return s
    # Some Hikvision event structures wrap data
    data = payload.get("data") or payload.get("Data") or None
    if isinstance(data, dict):
        for key in ("employeeNoString", "employeeNo", "personId"):
            v = data.get(key)
            if v:
                s = str(v).strip().upper()
                if s.startswith("FX") and len(s) == 7:
                    return s
    return None


def _action_from_device(device_type: str, payload: Dict[str, Any]) -> str:
    # device_type: entry/exit/universal
    # Use subEventType heuristics if available
    sub = str(payload.get("subEventType") or payload.get("SubEventType") or "").lower()
    if device_type == "entry":
        return "KIRDI"
    if device_type == "exit":
        return "CHIQDI"
    # universal:
    if "leave" in sub or "exit" in sub:
        return "CHIQDI"
    return "KIRDI"


async def _send_telegram_attendance(
    settings: Settings,
    chat_id: int,
    employee_name: str,
    employee_id: str,
    branch_name: str,
    action: str,
) -> None:
    dt = now_tz()
    text = (
        "✅ DAVOMAT\n\n"
        f"👤 Xodim: {employee_name} (FX: {employee_id})\n"
        f"🏢 Filial: {branch_name}\n"
        f"🔄 Holat: {action}\n"
        f"📅 Sana: {to_date_str(dt)}\n"
        f"⏰ Vaqt: {to_time_str(dt)}"
    )

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}

    try:
        timeout = httpx.Timeout(settings.TELEGRAM_NOTIFY_HTTP_TIMEOUT_SEC)
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
    except Exception as e:
        logger.exception("Telegram notify failed", extra={"chat_id": chat_id, "error": str(e)})