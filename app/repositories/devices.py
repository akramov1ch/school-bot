from __future__ import annotations

from sqlalchemy import select

from app.models.faceid import Device
from app.repositories.base import BaseRepository


class DeviceRepository(BaseRepository):
    async def create(self, *, branch_id: int, ip_address: str, username: str, password: str, device_type: str) -> Device:
        d = Device(branch_id=branch_id, ip_address=ip_address, username=username, password=password, device_type=device_type)
        self.session.add(d)
        await self.session.flush()
        return d

    async def get_by_ip(self, ip_address: str) -> Device | None:
        stmt = select(Device).where(Device.ip_address == ip_address)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_for_branch(self, branch_id: int) -> list[Device]:
        stmt = select(Device).where(Device.branch_id == branch_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())