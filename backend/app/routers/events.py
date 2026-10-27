"""Events & activities: event list with participation counts, bulk participation,
per-event summary (attended/absent + mandatory no-shows)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.models import AcademicYear, EventParticipation, SchoolEvent, Student, User
from app.models.events import EVENT_KINDS

router = APIRouter(prefix="/events", tags=["events"])


class EventIn(BaseModel):
    year_label: str = "2025-26"
    name: str
    kind: str = "meeting"  # sports|cultural|meeting|exam|holiday
    event_date: str  # YYYY-MM-DD
    is_mandatory: bool = False


class ParticipantIn(BaseModel):
    student_id: int
    attended: bool = True
    remark: str | None = None


@router.get("")
def list_events(year_label: str = Query("2025-26"), session: Session = Depends(get_session),
                user: User = Depends(require_roles("admin", "teacher", "parent", "student"))):
    year = session.exec(select(AcademicYear).where(AcademicYear.label == year_label)).first()
    if year is None:
        raise HTTPException(404, "academic year not found")
    events = session.exec(select(SchoolEvent).where(SchoolEvent.year_id == year.id)).all()
    counts = dict(session.exec(
        select(EventParticipation.event_id, func.count(EventParticipation.id))
        .where(EventParticipation.event_id.in_([e.id for e in events]))
        .group_by(EventParticipation.event_id)).all())
    return [{"id": e.id, "name": e.name, "kind": e.kind,
             "event_date": e.event_date.isoformat(), "is_mandatory": e.is_mandatory,
             "participation_count": counts.get(e.id, 0)} for e in events]


@router.post("")
def create_event(body: EventIn, session: Session = Depends(get_session),
                 user: User = Depends(require_roles("admin"))):
    if body.kind not in EVENT_KINDS:
        raise HTTPException(400, f"invalid kind: {body.kind} (one of {sorted(EVENT_KINDS)})")
    year = session.exec(select(AcademicYear).where(AcademicYear.label == body.year_label)).first()
    if year is None:
        raise HTTPException(404, "academic year not found")
    event = SchoolEvent(year_id=year.id, name=body.name, kind=body.kind,
                       event_date=date.fromisoformat(body.event_date),
                       is_mandatory=body.is_mandatory)
    session.add(event)
    session.commit()
    session.refresh(event)
    record(session, actor=user.username, action="create", resource=f"event#{event.id}",
           detail={"name": event.name, "kind": event.kind})
    return {"id": event.id, "name": event.name, "kind": event.kind,
            "event_date": event.event_date.isoformat(), "is_mandatory": event.is_mandatory,
            "year_label": year.label}


@router.post("/{event_id}/participate")
def participate(event_id: int, body: list[ParticipantIn], session: Session = Depends(get_session),
                user: User = Depends(require_roles("admin", "teacher"))):
    event = session.get(SchoolEvent, event_id)
    if event is None:
        raise HTTPException(404, "event not found")
    written = 0
    for p in body:
        # upsert: one participation row per (event, student)
        existing = session.exec(select(EventParticipation).where(
            EventParticipation.event_id == event.id,
            EventParticipation.student_id == p.student_id)).first()
        if existing:
            existing.attended = p.attended
            existing.remark = p.remark
            session.add(existing)
        else:
            session.add(EventParticipation(event_id=event.id, student_id=p.student_id,
                                           attended=p.attended, remark=p.remark))
        written += 1
    session.commit()
    record(session, actor=user.username, action="update", resource=f"event#{event_id}",
           detail={"participations": written})
    return {"event_id": event_id, "written": written}


@router.get("/{event_id}/summary")
def event_summary(event_id: int, session: Session = Depends(get_session),
                  user: User = Depends(require_roles("admin", "teacher"))):
    event = session.get(SchoolEvent, event_id)
    if event is None:
        raise HTTPException(404, "event not found")
    parts = session.exec(select(EventParticipation).where(
        EventParticipation.event_id == event.id)).all()
    attended = sum(1 for p in parts if p.attended)
    absent = len(parts) - attended
    # no-show list only matters for mandatory events
    missing = [p.student_id for p in parts if not p.attended] if event.is_mandatory else []
    names = {s.id: s.name for s in
             session.exec(select(Student).where(Student.id.in_(missing))).all()} if missing else {}
    return {
        "event_id": event_id, "name": event.name, "is_mandatory": event.is_mandatory,
        "recorded": len(parts), "attended": attended, "absent": absent,
        "mandatory_not_attended": [
            {"student_id": sid, "name": names.get(sid, "")} for sid in sorted(missing)],
    }
