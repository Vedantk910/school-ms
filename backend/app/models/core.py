"""Core academic domain: boards, years, classes, subjects, schemes, holidays, staff."""
from datetime import date

from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Date, Integer, String, Text, UniqueConstraint, ForeignKey

from app.db import Base


class Board(Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)  # MSBSHSE, CBSE, ICSE
    name: str


class AcademicYear(Base, table=True):
    __tablename__ = "academic_year"
    id: int | None = Field(default=None, primary_key=True)
    board_id: int = Field(foreign_key="board.id")
    label: str = Field(unique=True, index=True)  # "2025-26"
    start_date: date = Column(Date, nullable=False)
    end_date: date = Column(Date, nullable=False)
    asof_date: date = Column(Date, nullable=False)  # dataset as-of (2026-06-30)


class ClassSection(Base, table=True):
    """A cohort: class level + section within a school-year."""
    __tablename__ = "class_section"
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    level: int = Field(index=True)  # 6..10
    section: str = Field(default="A")
    __table_args__ = (UniqueConstraint("year_id", "level", "section"),)


class Subject(Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True)  # EN, MA, HI, M, S, SS, C, IT
    name: str
    medium: str = Field(default="english")  # english | marathi | hindi


class SubjectScheme(Base, table=True):
    """How a subject is assessed in a given level/year. Board-aware split lives here.
    MSBSHSE HSC Std 10 example: Maths theory 40 + practical 60 (max 100)."""
    __tablename__ = "subject_scheme"
    id: int | None = Field(default=None, primary_key=True)
    subject_id: int = Field(foreign_key="subject.id", index=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    level: int
    theory_max: int
    practical_max: int

    @property
    def total_max(self) -> int:
        return self.theory_max + self.practical_max


class Teacher(Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    staff_code: str = Field(index=True)
    subject_ids: list = Field(default_factory=list, sa_column=Column(Text, default="[]"))


class Holiday(Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    d: date = Column(Date, nullable=False)
    name: str
