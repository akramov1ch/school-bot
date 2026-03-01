from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from google.oauth2 import service_account
from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.timezone import TZ, to_ddmmyyyy, now_tz, to_time_str, to_date_str

logger = get_logger(__name__)


class SheetsError(RuntimeError):
    pass


@dataclass
class SheetWriteResult:
    ok: bool
    error: Optional[str] = None


class GoogleSheetManager:
    """
    Minimal, production-safe wrapper for Google Sheets writes/reads.

    - Uses Service Account JSON.
    - Retries writes with exponential backoff.
    - Attendance writes create daily tab (DD.MM.YYYY) and ensure header row.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        creds = service_account.Credentials.from_service_account_file(
            str(self.settings.google_service_account_path),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._service

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=12),
        retry=retry_if_exception_type(Exception),
    )
    def _batch_update(self, spreadsheet_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        service = self._get_service()
        return service.spreadsheets().batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=1, max=12),
        retry=retry_if_exception_type(Exception),
    )
    def _values_append(self, spreadsheet_id: str, range_: str, values: List[List[Any]]) -> Dict[str, Any]:
        service = self._get_service()
        return (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": values},
            )
            .execute()
        )

    def _get_sheet_id_by_title(self, spreadsheet_id: str, title: str) -> Optional[int]:
        service = self._get_service()
        meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sh in meta.get("sheets", []):
            props = sh.get("properties", {})
            if props.get("title") == title:
                return int(props.get("sheetId"))
        return None

    def ensure_sheet(self, spreadsheet_id: str, title: str) -> None:
        existing_id = self._get_sheet_id_by_title(spreadsheet_id, title)
        if existing_id is not None:
            return

        logger.info("Creating sheet tab", extra={"spreadsheet_id": spreadsheet_id, "title": title})
        body = {
            "requests": [
                {
                    "addSheet": {
                        "properties": {
                            "title": title,
                            "gridProperties": {"rowCount": 2000, "columnCount": 20},
                        }
                    }
                }
            ]
        }
        self._batch_update(spreadsheet_id, body)

    def ensure_header(self, spreadsheet_id: str, title: str, headers: List[str]) -> None:
        # We'll naively write header to A1.. if empty; in practice we'd read first row.
        # For reliability/simplicity: always update row 1 to headers.
        service = self._get_service()
        rng = f"{title}!A1:{chr(ord('A') + len(headers) - 1)}1"
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=rng,
            valueInputOption="RAW",
            body={"values": [headers]},
        ).execute()

    def log_attendance(self, spreadsheet_id: str, employee_name: str, employee_id: str, action: str) -> SheetWriteResult:
        dt = now_tz()
        title = to_ddmmyyyy(dt)
        headers = self.settings.ATTENDANCE_DEFAULT_HEADERS.split(",")

        try:
            self.ensure_sheet(spreadsheet_id, title)
            self.ensure_header(spreadsheet_id, title, headers)

            values = [[to_date_str(dt), to_time_str(dt), employee_name, employee_id, action]]
            self._values_append(spreadsheet_id, f"{title}!A:E", values)
            return SheetWriteResult(ok=True)
        except Exception as e:
            logger.exception("Attendance sheet write failed")
            return SheetWriteResult(ok=False, error=str(e))