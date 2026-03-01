from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HikDevice:
    ip_address: str
    username: str
    password: str
    device_type: str  # entry/exit/universal


class HikDeviceClient:
    """
    Hikvision device client (simplified, production-safe scaffolding):
    - Digest auth
    - upload_face(user_id, image_bytes)
    - set_access_group(user_id, group_id)

    NOTE: Exact Hikvision endpoints vary by firmware (ISAPI).
    This client is structured to be extended per your deployed model.
    """

    def __init__(self, settings: Settings, device: HikDevice) -> None:
        self.settings = settings
        self.device = device
        self.base_url = f"http://{device.ip_address}"
        self._auth = httpx.DigestAuth(device.username, device.password)

    async def _request(self, method: str, path: str, **kwargs):
        timeout = httpx.Timeout(self.settings.HIK_HTTP_TIMEOUT_SEC)
        async with httpx.AsyncClient(timeout=timeout, auth=self._auth) as client:
            url = self.base_url + path
            resp = await client.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp

    async def upload_face(self, user_id: str, image_bytes: bytes) -> dict:
        # Typical endpoint (may differ):
        # POST /ISAPI/Intelligent/FDLib/FaceDataRecord?format=json
        # with multipart: FaceDataRecord + face image
        files = {
            "FaceDataRecord": (
                None,
                f'{{"faceLibType":"blackFD","FDID":"1","FPID":"{user_id}"}}',
                "application/json",
            ),
            "img": ("face.jpg", image_bytes, "image/jpeg"),
        }
        try:
            resp = await self._request("POST", "/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json", files=files)
            return {"ok": True, "status_code": resp.status_code, "text": resp.text}
        except Exception as e:
            logger.exception("upload_face failed", extra={"ip": self.device.ip_address, "user_id": user_id})
            return {"ok": False, "error": str(e)}

    async def set_access_group(self, user_id: str, group_id: str) -> dict:
        # Placeholder endpoint; adapt to your model:
        # PUT /ISAPI/AccessControl/UserInfo/Modify?format=json
        payload = {
            "UserInfo": {
                "employeeNo": user_id,
                "userType": "normal",
                "Valid": {"enable": True},
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
                "belongGroup": group_id,
            }
        }
        try:
            resp = await self._request(
                "PUT",
                "/ISAPI/AccessControl/UserInfo/Modify?format=json",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            return {"ok": True, "status_code": resp.status_code, "text": resp.text}
        except Exception as e:
            logger.exception("set_access_group failed", extra={"ip": self.device.ip_address, "user_id": user_id})
            return {"ok": False, "error": str(e)}