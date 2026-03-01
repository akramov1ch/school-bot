from __future__ import annotations

from app.core.config import Settings
from app.core.security import hash_password
from app.core.utils import gen_password
from app.repositories.students import StudentRepository
from app.repositories.employees import EmployeeRepository


class CredentialService:
    def __init__(self, session) -> None:
        self.session = session
        self.settings = Settings()

    async def reset_student_password(self, student_uid: str) -> str | None:
        repo = StudentRepository(self.session)
        st = await repo.get_by_student_uid(student_uid)
        if not st:
            return None
        plain = gen_password(self.settings.PASSWORD_MIN_LEN, self.settings.PASSWORD_MAX_LEN)
        st.password_hash = hash_password(plain)
        self.session.add(st)
        return plain

    async def reset_employee_password(self, employee_uid: str) -> str | None:
        repo = EmployeeRepository(self.session)
        emp = await repo.get_by_employee_uid(employee_uid)
        if not emp:
            return None
        plain = gen_password(self.settings.PASSWORD_MIN_LEN, self.settings.PASSWORD_MAX_LEN)
        emp.password_hash = hash_password(plain)
        self.session.add(emp)
        return plain