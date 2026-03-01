from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.hik_device import HikDeviceClient, HikDevice
from app.core.logging import get_logger
from app.repositories.employees import EmployeeRepository
from app.repositories.devices import DeviceRepository

logger = get_logger(__name__)


class FaceEnrollmentService:
    """
    Employee selfie enrollment:
      - Find employee -> branch -> devices
      - Upload face to each device using HikDeviceClient
      - Mark employee.photo_status True if at least one succeeded
    """

    def __init__(self, session) -> None:
        self.session = session
        self.settings = Settings()

    async def enroll_employee_face(self, employee_id: int, image_bytes: bytes) -> list[dict[str, Any]]:
        emp_repo = EmployeeRepository(self.session)
        dev_repo = DeviceRepository(self.session)

        emp = await emp_repo.get_by_id(employee_id)
        if not emp or not emp.branch_id:
            return [{"ok": False, "device_ip": "-", "device_type": "-", "detail": "Branch topilmadi"}]

        devices = await dev_repo.list_for_branch(emp.branch_id)
        if not devices:
            return [{"ok": False, "device_ip": "-", "device_type": "-", "detail": "Device topilmadi"}]

        report: list[dict[str, Any]] = []
        any_ok = False
        for d in devices:
            client = HikDeviceClient(
                settings=self.settings,
                device=HikDevice(ip_address=d.ip_address, username=d.username, password=d.password, device_type=d.device_type),
            )
            r = await client.upload_face(user_id=emp.employee_uid, image_bytes=image_bytes)
            ok = bool(r.get("ok"))
            any_ok = any_ok or ok
            report.append({"ok": ok, "device_ip": d.ip_address, "device_type": d.device_type, "detail": r.get("error") or "OK"})

        if any_ok:
            emp.photo_status = True
            self.session.add(emp)

        return report