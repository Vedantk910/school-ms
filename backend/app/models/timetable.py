"""Timetable: weekly class-section grid + deterministic constraint-based auto-fill."""
from sqlmodel import Field, SQLModel
from sqlalchemy import UniqueConstraint

from app.db import Base


class TimetableSlot(Base, table=True):
    """One (day, slot) cell of a class section's weekly timetable."""
    __tablename__ = "timetable_slot"
    id: int | None = Field(default=None, primary_key=True)
    class_section_id: int = Field(foreign_key="class_section.id", index=True)
    day_of_week: int  # 1 = Mon .. 5 = Fri
    slot_index: int   # 1-based period within the day
    subject_id: int | None = Field(default=None, foreign_key="subject.id")
    teacher_id: int | None = Field(default=None, foreign_key="teacher.id")
    room: str | None = Field(default=None)

    __table_args__ = (
        UniqueConstraint("class_section_id", "day_of_week", "slot_index"),
    )
