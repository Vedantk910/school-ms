"""People: users, guardians, students, enrollment, admissions."""
from datetime import date, datetime

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Date, DateTime, String, Text, Boolean

from app.db import Base


class User(Base, table=True):
    """Login identity for any role (admin/teacher/parent/student).

    Table is named ``app_user``: ``user`` is a reserved word in PostgreSQL."""
    __tablename__ = "app_user"
    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(index=True)  # admin | teacher | parent | student
    full_name: str
    active: bool = True
    guardian_id: int | None = Field(default=None, foreign_key="guardian.id")
    student_id: int | None = Field(default=None, foreign_key="student.id")
    staff_code: str | None = Field(default=None)


class Guardian(Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    phone: str = Field(index=True)
    relation: str  # father | mother | other
    # DPDP Act 2023: guardian consent to process minor's data
    consent_given: bool = Field(default=False)
    consent_at: datetime | None = Field(default=None)
    aadhaar_masked: str | None = Field(default=None)  # e.g. "XXXX-XXXX-1234"


class Student(Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    admission_no: str = Field(index=True, unique=True)
    name: str
    uin_id: str | None = Field(default=None)  # U-Id, stored as given
    aadhaar_masked: str | None = Field(default=None)
    date_of_birth: date = Column(Date, nullable=False)
    gender: str = Field(default="M")
    guardian_ids: list = Field(default_factory=list, sa_column=Column(Text, default="[]"))
    address: str = Field(default="")
    active: bool = True  # False once withdrawn (kept in history for ML)


class Enrollment(Base, table=True):
    """Student's placement in a class-section for an academic year."""
    id: int | None = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    class_section_id: int = Field(foreign_key="class_section.id", index=True)
    status: str = Field(default="active", index=True)  # active | withdrew
    withdrawal_date: date | None = Column(Date, nullable=True)


class Admission(Base, table=True):
    """Admission funnel + compliance flags."""
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    stage: str = Field(index=True, default="enrolled")  # inquiry | applied | verified | enrolled | withdrawn
    rte_ews: bool = Field(default=False)  # RTE/EWS 25% quota seat
    admission_date: date = Column(Date, nullable=False)
