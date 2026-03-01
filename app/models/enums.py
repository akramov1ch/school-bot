from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    GUEST = "GUEST"
    PARENT = "PARENT"
    TEACHER = "TEACHER"
    HR = "HR"
    CASHIER = "CASHIER"
    CAREGIVER = "CAREGIVER"
    ADMIN = "ADMIN"


class EmployeeRole(str, enum.Enum):
    TEACHER = "TEACHER"
    HR = "HR"
    CASHIER = "CASHIER"
    CAREGIVER = "CAREGIVER"
    ADMIN = "ADMIN"


class StatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"


class HomeworkStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"


class FeedbackType(str, enum.Enum):
    SUGGESTION = "SUGGESTION"
    COMPLAINT = "COMPLAINT"