from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
import json

import httpx

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class HikDevice:
    ip_address: str
    username: str
    password: str
    device_type: str = "entry"  # entry/exit/universal


class HikDeviceClient:
    """
    Hikvision ISAPI client (async httpx + DigestAuth).

    Flow (based on your working requests sample):
      1) DELETE user by employeeNo (ignore errors)
      2) POST UserInfo/Record (if not 200 -> PUT Modify)
      3) POST FaceDataRecord (multipart: FaceDataRecord JSON + img JPEG)
      4) POST AccessGroup Record + Member Record (best-effort)
    """

    def __init__(
        self,
        settings: Settings,
        device: Optional[HikDevice] = None,
        ip_address: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        device_type: str = "entry",
    ):
        self.settings = settings

        # Legacy constructor support:
        if device is None:
            if not (ip_address and username is not None and password is not None):
                raise TypeError(
                    "HikDeviceClient requires either device=HikDevice(...) "
                    "or legacy args (ip_address, username, password, device_type)"
                )
            device = HikDevice(
                ip_address=str(ip_address),
                username=str(username),
                password=str(password),
                device_type=str(device_type or "entry"),
            )

        self.device: HikDevice = device
        self._timeout = httpx.Timeout(15.0, connect=10.0)
        self._verify_tls = False  # like requests verify=False

    @property
    def base_url(self) -> str:
        ip = self.device.ip_address.strip()
        # sample uses https://{ip}
        if ip.startswith("http://") or ip.startswith("https://"):
            return ip.rstrip("/")
        return f"https://{ip}"

    def _auth(self) -> httpx.Auth:
        return httpx.DigestAuth(self.device.username, self.device.password)

    def _url(self, path: str) -> str:
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, str]] = None,
        json_body: Optional[dict[str, Any]] = None,
        files: Optional[dict[str, Any]] = None,
        headers: Optional[dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> httpx.Response:
        url = self._url(path)

        async with httpx.AsyncClient(
            auth=self._auth(),
            timeout=(httpx.Timeout(timeout) if timeout else self._timeout),
            verify=self._verify_tls,
        ) as client:
            resp = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_body,
                files=files,
                headers=headers,
            )
        return resp

    async def set_access_group(self, user_id: str) -> bool:
        # 1) create group (best-effort)
        group_payload = {
            "AccessGroup": {
                "id": 1,
                "name": "AdminGroup",
                "enabled": True,
                "Attribute": {"templateNo": 1, "doorNo": 1},
            }
        }
        try:
            await self._request(
                "POST",
                "/ISAPI/AccessControl/AccessGroup/Record",
                params={"format": "json"},
                json_body=group_payload,
                timeout=10.0,
            )
        except Exception:
            pass

        # 2) add member
        member_payload = {
            "AccessGroupMemberList": [
                {"accessGroupID": 1, "UserList": [{"employeeNo": user_id}]}
            ]
        }
        try:
            resp = await self._request(
                "POST",
                "/ISAPI/AccessControl/AccessGroup/Member/Record",
                params={"format": "json"},
                json_body=member_payload,
                timeout=10.0,
            )
            return resp.status_code in (200, 201)
        except Exception:
            return False

    async def _ensure_user(self, user_id: str) -> tuple[bool, str]:
        start_time = "2020-01-01T00:00:00"
        end_time = "2035-01-01T00:00:00"

        user_payload = {
            "UserInfo": {
                "employeeNo": user_id,
                "userType": "normal",
                "doorRight": "1",
                "RightPlan": [{"doorNo": 1, "planTemplateNo": "1"}],
                "Valid": {"enable": True, "beginTime": start_time, "endTime": end_time},
            }
        }

        # delete best-effort
        try:
            del_payload = {
                "UserInfoDetail": {
                    "mode": "byEmployeeNo",
                    "EmployeeNoList": [{"employeeNo": user_id}],
                }
            }
            await self._request(
                "PUT",
                "/ISAPI/AccessControl/UserInfo/Delete",
                params={"format": "json"},
                json_body=del_payload,
                timeout=3.0,
            )
        except Exception:
            pass

        # create
        try:
            resp = await self._request(
                "POST",
                "/ISAPI/AccessControl/UserInfo/Record",
                params={"format": "json"},
                json_body=user_payload,
                timeout=10.0,
            )
            if resp.status_code == 200:
                return True, "OK"
        except Exception as e:
            return False, f"Ulanish xatosi (User): {e}"

        # modify
        try:
            resp2 = await self._request(
                "PUT",
                "/ISAPI/AccessControl/UserInfo/Modify",
                params={"format": "json"},
                json_body=user_payload,
                timeout=10.0,
            )
            if resp2.status_code in (200, 201):
                return True, "OK"
            return False, f"User modify error: {resp2.status_code} {resp2.text}"
        except Exception as e:
            return False, f"Ulanish xatosi (UserModify): {e}"

    async def upload_face(self, user_id: str, image_bytes: bytes) -> dict[str, Any]:
        # 1) Ensure user exists
        ok_user, msg_user = await self._ensure_user(user_id)
        if not ok_user:
            return {"ok": False, "error": msg_user}

        # 2) FaceDataRecord multipart
        face_url_path = "/ISAPI/Intelligent/FDLib/FaceDataRecord"
        face_data = {"faceLibType": "blackFD", "FDID": "1", "FPID": user_id}

        files = {
            "FaceDataRecord": (None, json.dumps(face_data), "application/json"),
            "img": ("face.jpg", image_bytes, "image/jpeg"),
        }

        resp = await self._request(
            "POST",
            face_url_path,
            params={"format": "json"},
            files=files,
            timeout=15.0,
        )

        # 3) best-effort access group
        try:
            await self.set_access_group(user_id)
        except Exception:
            pass

        # 4) Return detailed error
        if resp.status_code >= 400:
            return {
                "ok": False,
                "error": f"{resp.status_code} {resp.reason_phrase}",
                "body": resp.text,
            }

        # try JSON parse
        try:
            data = resp.json()
            if data.get("statusCode") == 1 or resp.status_code == 200:
                return {"ok": True, "body": data}
            return {"ok": False, "error": data.get("statusString") or "Unknown", "body": data}
        except Exception:
            return {"ok": True if resp.status_code == 200 else False, "body": resp.text}