from __future__ import annotations

from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.sheets import GoogleSheetManager
from app.repositories.payments import PaymentRepository

logger = get_logger(__name__)


class PaymentSheetWriter:
    """
    Writes payments to Google Sheets tab `payments`.
    If write fails:
      - mark payment.sheet_write_status = FAILED
      - retry later via scheduler job
    """

    def __init__(self, session) -> None:
        self.session = session
        self.settings = Settings()
        self.sheets = GoogleSheetManager(self.settings)

    async def enqueue_or_write(self, payment_id: int) -> None:
        # MVP: attempt immediately, fallback to FAILED for retry
        try:
            await self._write_once(payment_id)
        except Exception:
            logger.exception("Payment sheet write failed (immediate)")
            repo = PaymentRepository(self.session)
            await repo.mark_sheet_status(payment_id, "FAILED")

    async def retry_failed(self, limit: int = 20) -> int:
        repo = PaymentRepository(self.session)
        failed = await repo.list_failed_sheet_writes(limit=limit)
        n = 0
        for p in failed:
            try:
                await self._write_once(p.id)
                n += 1
            except Exception:
                logger.exception("Payment sheet write failed (retry)", extra={"payment_id": p.id})
                await repo.mark_sheet_status(p.id, "FAILED")
        return n

    async def _write_once(self, payment_id: int) -> None:
        repo = PaymentRepository(self.session)
        p = await repo.get_by_id(payment_id)
        if not p:
            return

        # Ensure header for 'payments' tab exists (simple update)
        headers = ["payment_id", "external_key", "amount", "currency", "paid_at", "cashier_employee_id", "method", "comment"]

        # Create/ensure tab
        self.sheets.ensure_sheet(self.settings.GOOGLE_SHEETS_SPREADSHEET_ID, "payments")
        self.sheets.ensure_header(self.settings.GOOGLE_SHEETS_SPREADSHEET_ID, "payments", headers)

        values = [[
            p.payment_code,
            p.student.external_key,
            float(p.amount),
            p.currency,
            p.paid_at.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
            p.cashier.employee_uid if p.cashier else "",
            p.method or "",
            p.comment or "",
        ]]

        # append with retries (inside GoogleSheetManager)
        self.sheets._values_append(self.settings.GOOGLE_SHEETS_SPREADSHEET_ID, "payments!A:H", values)

        await repo.mark_sheet_status(payment_id, "OK")