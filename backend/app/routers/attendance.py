"""Attendance: bulk daily register entry, class summary, leave requests."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func

from app.audit import record
from app.db import get_session
from app.dependencies import current_user, require_roles
from app.models import AcademicYear, Attendance, Enrollment, Student, User

router = APIRouter(prefix="/attendance", tags=["attendance"])

VALID_TYPES = {"P", "A", "L", "H"}


class RegisterIn(BaseModel):
    year_label: str = "2025-26"
    d: str  # YYYY-MM-DD
    section: str  # e.g. "7A"  -> level 7 section A
    entries: list[tuple[int, str]]  # [(student_id, type)]


@router.post("/register")
def register(body: RegisterIn, session: Session = Depends(get_session),
             user: User = Depends(require_roles("admin", "teacher"))):
    d = date.fromisoformat(body.d)
    for sid, t in body.entries:
        if t not in VALID_TYPES:
            raise HTTPException(400, f"invalid attendance type: {t}")
    year = session.exec(select(AcademicYear).where(AcademicYear.label == body.year_label)).first()
    if year is None:
        raise HTTPException(404, "academic year not found")
    level = int(body.section[:-1])
    sec_letter = body.section[-1]

    # Map each student in the request to their enrollment for this year + level.
    from app.models import ClassSection
    cs_ids = session.exec(select(ClassSection.id).where(
        ClassSection.year_id == year.id,
        ClassSection.level == level,
        ClassSection.section == sec_letter)).all()
    enr = session.exec(select(Enrollment).where(
        Enrollment.year_id == year.id,
        Enrollment.class_section_id.in_(list(cs_ids)))).all()
    enr_map = {e.student_id: e for e in enr}

    written = 0
    for sid, t in body.entries:
        e = enr_map.get(sid)
        if e is None:
            continue
        existing = session.exec(select(Attendance).where(
            Attendance.enrollment_id == e.id, Attendance.d == d)).first()
        if existing:
            existing.type = t
            session.add(existing)
        else:
            session.add(Attendance(enrollment_id=e.id, year_id=year.id, d=d, type=t))
        written += 1
    session.commit()
    record(session, actor=user.username, action="create",
           resource=f"attendance/{body.section}/{d.isoformat()}",
           detail={"entries": written})
    return {"written": written, "date": d.isoformat(), "section": body.section}


@router.get("/summary")
def summary(section: str = "7A", session: Session = Depends(get_session),
            user: User = Depends(require_roles("admin", "teacher"))):
    year = session.exec(select(AcademicYear).where(AcademicYear.label == "2025-26")).first()
    enr = session.exec(select(Enrollment).where(
        Enrollment.year_id == year.id)).all()
    enr_ids = [e.id for e in enr]
    total = session.exec(select(func.count(Attendance.id)).where(
        Attendance.enrollment_id.in_(enr_ids))).one()
    present = session.exec(select(func.count(Attendance.id)).where(
        Attendance.enrollment_id.in_(enr_ids), Attendance.type == "P")).one()
    absent = session.exec(select(func.count(Attendance.id)).where(
        Attendance.enrollment_id.in_(enr_ids), Attendance.type == "A")).one()
    leave = session.exec(select(func.count(Attendance.id)).where(
        Attendance.enrollment_id.in_(enr_ids), Attendance.type == "L")).one()
    return {"total": total, "present": present, "absent": absent, "leave": leave,
            "present_pct": round(100 * present / total, 1) if total else 0.0}
