from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import secrets

from google.oauth2 import service_account
from googleapiclient.discovery import build
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.logging import get_logger
from app.core.security import hash_password
from app.core.utils import gen_password, dumps_json
from app.repositories.sync_logs import SyncLogRepository
from app.repositories.classes import ClassRepository
from app.repositories.students import StudentRepository
from app.repositories.employees import EmployeeRepository
from app.repositories.class_subjects import ClassSubjectRepository
from app.repositories.branches import BranchRepository

logger = get_logger(__name__)


@dataclass
class SyncResult:
    classes: int = 0
    students: int = 0
    employees: int = 0
    class_subjects: int = 0


class SheetsSyncService:
    """
    Google Sheets -> DB sync

    UID generation (NEW records only):
      - Employee: FX + 5-digit random (e.g., FX81247)
      - Student:  FM + 5-digit random (e.g., FM81247)

    Uniqueness guarantee:
      - DB UNIQUE constraint on employee_uid / student_uid
      - On collision: SAVEPOINT rollback + retry (no O(n), no race).
    """

    def __init__(self, session) -> None:
        self.session = session
        self.settings = Settings()
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service
        creds = service_account.Credentials.from_service_account_file(
            str(self.settings.google_service_account_path),
            # Scope o'zgartirildi: endi yozishga ham ruxsat bor
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        self._service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return self._service

    def _read_tab(self, tab: str) -> list[list[str]]:
        service = self._get_service()
        sheet_id = self.settings.GOOGLE_SHEETS_SPREADSHEET_ID
        resp = service.spreadsheets().values().get(spreadsheetId=sheet_id, range=f"{tab}!A:Z").execute()
        values = resp.get("values", [])
        return values

    def _write_back_credentials(self, tab: str, row_idx: int, uid: str, password: str):
        """ID va parolni jadvalning G va H ustunlariga yozadi"""
        try:
            service = self._get_service()
            sheet_id = self.settings.GOOGLE_SHEETS_SPREADSHEET_ID
            # G ustuni - ID, H ustuni - password
            range_name = f"{tab}!G{row_idx}:H{row_idx}"
            values = [[uid, password]]
            body = {"values": values}
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range=range_name,
                valueInputOption="RAW",
                body=body
            ).execute()
        except Exception as e:
            logger.error(f"Jadvalga yozishda xatolik ({tab}, row {row_idx}): {e}")

    @staticmethod
    def _rows_to_dicts(values: list[list[str]]) -> list[dict[str, str]]:
        if not values:
            return []
        header = [h.strip() for h in values[0]]
        out: list[dict[str, str]] = []
        for row in values[1:]:
            d = {}
            for i, h in enumerate(header):
                d[h] = row[i].strip() if i < len(row) else ""
            if any(v for v in d.values()):
                out.append(d)
        return out

    @staticmethod
    def _gen_uid(prefix: str) -> str:
        # 5 xonali: 10000..99999
        n = secrets.randbelow(90000) + 10000
        return f"{prefix}{n}"

    async def sync_all(self) -> str:
        repo = SyncLogRepository(self.session)
        result = SyncResult()

        try:
            result.classes = await self._sync_classes()
            await repo.create(type_="classes", status="OK", payload_json=dumps_json({"count": result.classes}))
        except Exception as e:
            await repo.create(type_="classes", status="FAILED", payload_json=dumps_json({"error": str(e)}))
            raise

        try:
            result.employees = await self._sync_employees()
            await repo.create(type_="employees", status="OK", payload_json=dumps_json({"count": result.employees}))
        except Exception as e:
            await repo.create(type_="employees", status="FAILED", payload_json=dumps_json({"error": str(e)}))
            raise

        try:
            result.students = await self._sync_students()
            await repo.create(type_="students", status="OK", payload_json=dumps_json({"count": result.students}))
        except Exception as e:
            await repo.create(type_="students", status="FAILED", payload_json=dumps_json({"error": str(e)}))
            raise

        try:
            result.class_subjects = await self._sync_class_subjects()
            await repo.create(type_="class_subjects", status="OK", payload_json=dumps_json({"count": result.class_subjects}))
        except Exception as e:
            await repo.create(type_="class_subjects", status="FAILED", payload_json=dumps_json({"error": str(e)}))
            raise

        return f"classes={result.classes}, employees={result.employees}, students={result.students}, class_subjects={result.class_subjects}"

    async def _sync_classes(self) -> int:
        values = self._read_tab("classes")
        rows = self._rows_to_dicts(values)
        repo = ClassRepository(self.session)
        count = 0
        for r in rows:
            class_name = r.get("class_name", "")
            status = r.get("status", "active") or "active"
            if not class_name:
                continue
            await repo.upsert(class_name=class_name, status=status)
            count += 1
        await self.session.flush()
        return count

    async def _sync_employees(self) -> int:
        values = self._read_tab("employees")
        rows = self._rows_to_dicts(values)
        emp_repo = EmployeeRepository(self.session)
        branch_repo = BranchRepository(self.session)

        count = 0

        for i, r in enumerate(rows):
            row_num = i + 2  # 1-qator header, shuning uchun +2
            external_key = r.get("external_key") or None
            full_name = r.get("full_name", "")
            role = (r.get("role", "") or "").strip().upper()
            subject = r.get("subject") or None
            status = (r.get("status", "active") or "active").strip().lower()
            branch_name = r.get("branch_name") or None
            phone = r.get("phone") or None

            if not full_name or not role:
                continue

            branch_id = None
            if branch_name:
                b = await branch_repo.get_by_name(branch_name)
                if b:
                    branch_id = b.id

            existing = None
            if external_key:
                existing = await emp_repo.get_by_external_key(external_key)

            # Existing bo'lsa — UID/password o'zgartirmaymiz
            if existing:
                employee_uid = existing.employee_uid
                password_hash = ""
                await emp_repo.upsert_from_sheet(
                    external_key=external_key,
                    employee_uid=employee_uid,
                    password_hash=password_hash,
                    full_name=full_name,
                    role=role,
                    subject=subject if role == "TEACHER" else None,
                    status=status,
                    branch_id=branch_id,
                    phone=phone,
                )
                count += 1
                continue

            # NEW employee — random UID + password, collision bo'lsa retry
            plain_password = gen_password(self.settings.PASSWORD_MIN_LEN, self.settings.PASSWORD_MAX_LEN)
            password_hash = hash_password(plain_password)

            max_tries = 30
            last_err: Exception | None = None

            for _ in range(max_tries):
                employee_uid = self._gen_uid("FX")

                try:
                    async with self.session.begin_nested():
                        await emp_repo.upsert_from_sheet(
                            external_key=external_key,
                            employee_uid=employee_uid,
                            password_hash=password_hash,
                            full_name=full_name,
                            role=role,
                            subject=subject if role == "TEACHER" else None,
                            status=status,
                            branch_id=branch_id,
                            phone=phone,
                        )
                        # UNIQUE tekshiruv flush vaqtida chiqadi
                        await self.session.flush()

                    # DB muvaffaqiyatli -> endi sheetsga yozamiz
                    self._write_back_credentials("employees", row_num, employee_uid, plain_password)

                    last_err = None
                    break

                except IntegrityError as e:
                    # UID collision (unique violation) bo'lishi mumkin -> retry
                    last_err = e
                    # begin_nested rollback bo'ladi, biz tashqi tranzaksiyani buzmaymiz
                    continue

            if last_err is not None:
                logger.error(f"Employee UID collision: {max_tries} urinishda ham unique topilmadi (row={row_num})")
                raise last_err

            count += 1

        await self.session.flush()
        return count

    async def _sync_students(self) -> int:
        values = self._read_tab("students")
        rows = self._rows_to_dicts(values)
        class_repo = ClassRepository(self.session)
        student_repo = StudentRepository(self.session)

        count = 0

        for i, r in enumerate(rows):
            row_num = i + 2
            external_key = r.get("external_key", "")
            full_name = r.get("full_name", "")
            class_name = r.get("class_name", "")
            status = (r.get("status", "active") or "active").strip().lower()
            notes = r.get("notes") or None

            if not external_key or not full_name or not class_name:
                continue

            cls = await class_repo.get_by_name(class_name)
            if not cls:
                cls = await class_repo.upsert(class_name=class_name, status="active")

            existing = await student_repo.get_by_external_key(external_key)

            # Existing bo'lsa — UID/password o'zgartirmaymiz
            if existing:
                student_uid = existing.student_uid
                password_hash = ""
                await student_repo.upsert_from_sheet(
                    external_key=external_key,
                    student_uid=student_uid,
                    password_hash=password_hash,
                    full_name=full_name,
                    class_id=cls.id,
                    status=status,
                    notes=notes,
                )
                count += 1
                continue

            # NEW student — random UID + password, collision bo'lsa retry
            plain_password = gen_password(self.settings.PASSWORD_MIN_LEN, self.settings.PASSWORD_MAX_LEN)
            password_hash = hash_password(plain_password)

            max_tries = 30
            last_err: Exception | None = None

            for _ in range(max_tries):
                student_uid = self._gen_uid("FM")

                try:
                    async with self.session.begin_nested():
                        await student_repo.upsert_from_sheet(
                            external_key=external_key,
                            student_uid=student_uid,
                            password_hash=password_hash,
                            full_name=full_name,
                            class_id=cls.id,
                            status=status,
                            notes=notes,
                        )
                        await self.session.flush()

                    # DB muvaffaqiyatli -> endi sheetsga yozamiz
                    self._write_back_credentials("students", row_num, student_uid, plain_password)

                    last_err = None
                    break

                except IntegrityError as e:
                    last_err = e
                    continue

            if last_err is not None:
                logger.error(f"Student UID collision: {max_tries} urinishda ham unique topilmadi (row={row_num})")
                raise last_err

            count += 1

        await self.session.flush()
        return count

    async def _sync_class_subjects(self) -> int:
        values = self._read_tab("class_subjects")
        rows = self._rows_to_dicts(values)
        class_repo = ClassRepository(self.session)
        emp_repo = EmployeeRepository(self.session)
        cs_repo = ClassSubjectRepository(self.session)

        grouped: dict[str, list[dict[str, str]]] = {}
        for r in rows:
            cn = r.get("class_name", "")
            if not cn:
                continue
            grouped.setdefault(cn, []).append(r)

        total = 0
        for class_name, items in grouped.items():
            cls = await class_repo.get_by_name(class_name)
            if not cls:
                continue
            repl: list[tuple[str, int, str | None]] = []
            for it in items:
                subject = it.get("subject_name", "")
                teacher_uid = (it.get("teacher_employee_id", "") or "").strip().upper()
                status = (it.get("status") or "active").strip().lower()
                if not subject or not teacher_uid:
                    continue
                emp = await emp_repo.get_by_employee_uid(teacher_uid)
                if not emp:
                    continue
                repl.append((subject, emp.id, status))
            if repl:
                await cs_repo.replace_for_class(cls.id, repl)
                total += len(repl)
        await self.session.flush()
        return total