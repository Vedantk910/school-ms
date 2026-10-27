"""Events & activities: school events/clubs and student participation."""
from datetime import date

from sqlmodel import Field
from sqlalchemy import Column, Date, UniqueConstraint

from app.db import Base

EVENT_KINDS = {"sports", "cultural", "meeting", "exam", "holiday"}


class SchoolEvent(Base, table=True):
    """A dated school event (sports day, cultural festival, PTA meeting, exam, holiday)."""
    __tablename__ = "school_event"
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    name: str
    kind: str = Field(index=True, default="meeting")  # sports|cultural|meeting|exam|holiday
    event_date: date = Column(Date, nullable=False)
    is_mandatory: bool = Field(default=False)


class EventParticipation(Base, table=True):
    """One row per student-event: whether the student attended, plus an optional remark."""
    __tablename__ = "event_participation"
    id: int | None = Field(default=None, primary_key=True)
    event_id: int = Field(foreign_key="school_event.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    attended: bool = Field(default=True)
    remark: str | None = Field(default=None)
    __table_args__ = (UniqueConstraint("event_id", "student_id"),)
