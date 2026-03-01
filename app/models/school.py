from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UserRole, EmployeeRole, StatusEnum, HomeworkStatus, FeedbackType


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[UserRole] = mapped_column(String(32), nullable=False, default=UserRole.GUEST.value)
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    employee = relationship("Employee", lazy="joined")


class Class(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=StatusEnum.active.value)


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    student_uid: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)  # FM12345
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=StatusEnum.active.value)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    cls = relationship("Class", lazy="joined")


class ParentStudent(Base):
    __tablename__ = "parent_student"
    __table_args__ = (UniqueConstraint("parent_user_id", "student_id", name="uq_parent_student"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student = relationship("Student", lazy="joined")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_key: Mapped[Optional[str]] = mapped_column(String(128), unique=True, nullable=True, index=True)
    employee_uid: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)  # FX12345
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # TEACHER/HR/CASHIER/CAREIGVER/ADMIN
    subject: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=StatusEnum.active.value)

    branch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)
    photo_status: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notification_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    phone: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ClassSubject(Base):
    __tablename__ = "class_subjects"
    __table_args__ = (UniqueConstraint("class_id", "subject_name", name="uq_class_subject"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(128), nullable=False)
    teacher_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True, default=StatusEnum.active.value)

    cls = relationship("Class", lazy="joined")
    teacher = relationship("Employee", lazy="joined")


class Grade(Base):
    __tablename__ = "grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)

    subject_name: Mapped[str] = mapped_column(String(128), nullable=False)
    teacher_employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    score: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD (keep as string to match Sheets)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    student = relationship("Student", lazy="joined")
    cls = relationship("Class", lazy="joined")
    teacher = relationship("Employee", lazy="joined")


class Homework(Base):
    __tablename__ = "homeworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_name: Mapped[str] = mapped_column(String(128), nullable=False)
    teacher_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)
    deadline: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # YYYY-MM-DD
    attachment_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default=HomeworkStatus.ACTIVE.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cls = relationship("Class", lazy="joined")
    teacher = relationship("Employee", lazy="joined")


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_teacher_employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)  # PARENT/MANAGEMENT
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    teacher = relationship("Employee", lazy="joined")
    student = relationship("Student", lazy="joined")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    from_parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # SUGGESTION/COMPLAINT
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_seen_by_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payment_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="UZS")
    method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cashier_employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sheet_write_status: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # OK/FAILED/PENDING

    student = relationship("Student", lazy="joined")
    cashier = relationship("Employee", lazy="joined")