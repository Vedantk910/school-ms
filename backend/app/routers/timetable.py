"""Timetable: weekly grid lookup + deterministic constraint-solver auto-fill."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.models import User
from app.models.timetable import TimetableSlot
from app.timetable_solver import fill_week

router = APIRouter(prefix="/timetable", tags=["timetable"])


class SubjectSpec(BaseModel):
    subject_id: int
    periods: int
    teachers: list[int] | None = None


class ConflictIn(BaseModel):
    teacher_id: int
    day: int
    slot: int


class SolveIn(BaseModel):
    class_section_id: int
    slots_per_day: int = 4
    subjects: list[SubjectSpec]
    teachers: list[dict] | None = None
    conflicts: list[ConflictIn] | None = None
    seed: int = 42


@router.get("")
def cell(class_section_id: int, day: int = Query(...), slot: int = Query(...),
         session: Session = Depends(get_session),
         user: User = Depends(require_roles("admin", "teacher", "parent", "student"))):
    s = session.exec(select(TimetableSlot).where(
        TimetableSlot.class_section_id == class_section_id,
        TimetableSlot.day_of_week == day, TimetableSlot.slot_index == slot)).first()
    return {"class_section_id": class_section_id, "day": day, "slot": slot,
            "subject_id": s.subject_id if s else None,
            "teacher_id": s.teacher_id if (s and s.teacher_id is not None) else None}


@router.get("/grid")
def grid(class_section_id: int, session: Session = Depends(get_session),
         user: User = Depends(require_roles("admin", "teacher", "parent", "student"))):
    slots = session.exec(select(TimetableSlot).where(
        TimetableSlot.class_section_id == class_section_id)).all()
    grid: dict[tuple[int, int], dict] = {}
    for s in slots:
        grid[(s.day_of_week, s.slot_index)] = {"subject_id": s.subject_id,
                                               "teacher_id": s.teacher_id}
    weeks = {}
    for s in slots:
        d = weeks.setdefault(s.day_of_week, [])
        d.append({"slot": s.slot_index, "subject_id": s.subject_id, "teacher_id": s.teacher_id})
    return {"class_section_id": class_section_id, "days": [
        {"day": day, "cells": sorted(cells, key=lambda c: c["slot"])}
        for day, cells in sorted(weeks.items())]}


@router.post("/solve")
def solve(body: SolveIn, session: Session = Depends(get_session),
          user: User = Depends(require_roles("admin", "teacher"))):
    subjects = [{"subject_id": s.subject_id, "periods": s.periods,
                 "teachers": s.teachers or []} for s in body.subjects]
    conflicts = [{"teacher_id": c.teacher_id, "day": c.day, "slot": c.slot}
                 for c in (body.conflicts or [])]
    plan = fill_week(body.class_section_id, body.slots_per_day, subjects,
                     conflicts=conflicts, seed=body.seed)
    if not plan["solved"]:
        raise HTTPException(400, {"detail": "timetable infeasible", "reason": plan["reason"]})
    # rewrite this section's week
    for old in session.exec(select(TimetableSlot).where(
            TimetableSlot.class_section_id == body.class_section_id)).all():
        session.delete(old)
    session.flush()
    for day, slot, sid, tid in plan["assignments"]:
        session.add(TimetableSlot(class_section_id=body.class_section_id, day_of_week=day,
                                  slot_index=slot, subject_id=sid, teacher_id=tid))
    session.commit()
    record(session, actor=user.username, action="update",
           resource=f"timetable#{body.class_section_id}",
           detail={"seed": body.seed, "cells": len(plan["assignments"])})
    return {"class_section_id": body.class_section_id, "solved": True,
            "seed": body.seed, "assignments": [
                {"day": d, "slot": s, "subject_id": sid, "teacher_id": t}
                for d, s, sid, t in plan["assignments"]]}
