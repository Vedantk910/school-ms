"""Academic: attendance, exams, papers, marks, results."""
from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Date, DateTime, String, Text, Float, UniqueConstraint, ForeignKey

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Attendance(Base, table=True):
    """One row per student-class-section-day. Types: P A L H (present/absent/leave/holiday)."""
    id: int | None = Field(default=None, primary_key=True)
    enrollment_id: int = Field(foreign_key="enrollment.id", index=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    d: date = Column(Date, nullable=False, index=True)
    type: str = Field(default="P", index=True)  # P A L H
    leave_reason: str | None = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("enrollment_id", "d", name="uq_attendance_enroll_day"),
    )


class Exam(Base, table=True):
    """An exam session: internal (CIA) or external (pre-board/board)."""
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    name: str  # "Internal 1", "Pre-Board", "HSC Board"
    type: str = Field(index=True, default="internal")  # internal | external
    window_start: date = Column(Date, nullable=False)
    window_end: date = Column(Date, nullable=False)
    weight_pct: float = Field(default=0.0)  # contribution to final


class ExamPaper(Base, table=True):
    """A subject's paper within an exam, with its max marks."""
    __tablename__ = "exam_paper"
    id: int | None = Field(default=None, primary_key=True)
    exam_id: int = Field(foreign_key="exam.id", index=True)
    subject_id: int = Field(foreign_key="subject.id", index=True)
    theory_max: int
    practical_max: int = Field(default=0)
    __table_args__ = (UniqueConstraint("exam_id", "subject_id"),)


class Mark(Base, table=True):
    """A student's score on one paper. Grade is computed per MSBSHSE bands."""
    id: int | None = Field(default=None, primary_key=True)
    exam_paper_id: int = Field(foreign_key="exam_paper.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    theory: int | None
    practical: int | None
    total: int = Field(default=0)
    grade: str | None = Field(default=None)  # O A B C D E or FAIL
    pass_flag: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=_utcnow)
    __table_args__ = (UniqueConstraint("exam_paper_id", "student_id"),)


class Result(Base, table=True):
    """Frozen per-student-per-exam summary, published to parents."""
    id: int | None = Field(default=None, primary_key=True)
    exam_id: int = Field(foreign_key="exam.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    total_obtained: int
    total_possible: int
    percentage: float
    division: int = Field(default=1)
    division_rank: int | None
    overall_grade: str
    pass_count: int
    fail_count: int
    published_at: datetime | None = Field(default=None)
    __table_args__ = (UniqueConstraint("exam_id", "student_id"),)
