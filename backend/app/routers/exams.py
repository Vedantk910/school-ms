"""Exams & gradebook: exam calendar, bulk mark entry, MSBSHSE grade computation,
class/division aggregates, result publication."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.models import (
    AcademicYear, Exam, ExamPaper, Mark, Result, Student, User,
)

router = APIRouter(prefix="/exams", tags=["exams"])


def msbshse_grade(pct: float) -> tuple[str, bool]:
    """MSBSHSE HSC grade bands. Returns (grade, pass_flag)."""
    if pct >= 90:
        return "O", True
    if pct >= 80:
        return "A", True
    if pct >= 70:
        return "B", True
    if pct >= 60:
        return "C", True
    if pct >= 50:
        return "D", True
    if pct >= 33:
        return "E", True
    return "F", False


class MarkIn(BaseModel):
    student_id: int
    theory: int
    practical: int | None = None
    subject_code: str | None = None  # e.g. "M" -> targets that subject's paper


class BulkMarksIn(BaseModel):
    exam_id: int
    marks: list[MarkIn]


@router.get("")
def list_exams(year_label: str = Query("2025-26"), session: Session = Depends(get_session),
               user: User = Depends(require_roles("admin", "teacher", "parent", "student"))):
    year = session.exec(select(AcademicYear).where(AcademicYear.label == year_label)).first()
    rows = session.exec(select(Exam).where(Exam.year_id == year.id)).all()
    return [{"id": e.id, "name": e.name, "type": e.type, "weight_pct": e.weight_pct,
             "window": f"{e.window_start} .. {e.window_end}"} for e in rows]


@router.get("/{exam_id}/results")
def exam_results(exam_id: int, session: Session = Depends(get_session),
                 user: User = Depends(require_roles("admin", "teacher", "parent", "student"))):
    exam = session.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(404, "exam not found")
    results = session.exec(select(Result).where(Result.exam_id == exam_id)).all()
    students = {s.id: s for s in session.exec(select(Student)).all()}
    avg = sum(r.percentage for r in results) / len(results) if results else 0.0
    top = sorted(results, key=lambda r: -r.percentage)[:10]
    return {
        "exam_id": exam_id, "name": exam.name, "examined": len(results),
        "avg_pct": round(avg, 2),
        "pass_rate": round(100 * sum(1 for r in results if r.division <= 2) / len(results), 1)
        if results else 0.0,
        "top": [
            {"student_id": r.student_id, "name": students.get(r.student_id, Student()).name,
             "pct": r.percentage, "grade": r.overall_grade, "division": r.division}
            for r in top
        ],
        "results": [
            {"student_id": r.student_id, "pct": r.percentage, "grade": r.overall_grade,
             "division": r.division, "pass": r.pass_count, "fail": r.fail_count}
            for r in sorted(results, key=lambda r: -r.percentage)
        ],
    }


@router.post("/{exam_id}/marks")
def enter_marks(exam_id: int, body: BulkMarksIn, session: Session = Depends(get_session),
                user: User = Depends(require_roles("admin", "teacher"))):
    from app.models import Subject
    exam = session.get(Exam, exam_id)
    if exam is None:
        raise HTTPException(404, "exam not found")
    papers = {p.subject_id: p for p in
              session.exec(select(ExamPaper).where(ExamPaper.exam_id == exam.id)).all()}
    subj_id_by_code = {s.code: s.id for s in session.exec(select(Subject)).all()}
    written = 0
    for m in body.marks:
        # resolve the target paper: by subject_code when provided, else the first paper
        if m.subject_code and m.subject_code in subj_id_by_code:
            target = papers.get(subj_id_by_code[m.subject_code])
        else:
            target = next(iter(papers.values()), None)
        if target is None:
            raise HTTPException(400, f"no paper for subject {m.subject_code or 'first'} in this exam")
        total = m.theory + (m.practical or 0)
        max_total = target.theory_max + target.practical_max
        if total > max_total:
            raise HTTPException(400, f"marks exceed max ({max_total}) for subject {target.subject_id}")
        pct = 100 * total / max_total if max_total else 0
        grade, passed = msbshse_grade(pct)
        # upsert: one mark per (paper, student)
        existing = session.exec(select(Mark).where(Mark.exam_paper_id == target.id,
                                                    Mark.student_id == m.student_id)).first()
        if existing:
            existing.theory = m.theory
            existing.practical = m.practical or 0
            existing.total = total
            existing.grade = grade
            existing.pass_flag = passed
            session.add(existing)
        else:
            session.add(Mark(exam_paper_id=target.id, student_id=m.student_id, theory=m.theory,
                             practical=m.practical or 0, total=total, grade=grade,
                             pass_flag=passed))
        written += 1
    session.flush()
    # recompute results for EVERY student with marks in this exam + division ranks
    for r in session.exec(select(Result).where(Result.exam_id == exam.id)).all():
        session.delete(r)
    session.flush()
    paper_max = {p.id: p.theory_max + p.practical_max for p in papers.values()}
    result_list: list[tuple[int, int, int]] = []  # (sid, tot, poss)
    all_mks = session.exec(select(Mark).join(ExamPaper, ExamPaper.id == Mark.exam_paper_id)
                          .where(ExamPaper.exam_id == exam.id)).all()
    per_student: dict[int, list[Mark]] = {}
    for mk in all_mks:
        per_student.setdefault(mk.student_id, []).append(mk)
    for sid, mks in per_student.items():
        tot = sum(mk.total for mk in mks)
        poss = sum(paper_max[mk.exam_paper_id] for mk in mks)
        pct = 100 * tot / poss if poss else 0
        grade, _ = msbshse_grade(pct)
        division = 1 if pct >= 60 else (2 if pct >= 40 else 3)
        result_list.append((sid, tot, poss))
        session.add(Result(exam_id=exam.id, student_id=sid, total_obtained=tot,
                           total_possible=poss, percentage=round(pct, 2),
                           division=division, division_rank=None, overall_grade=grade,
                           pass_count=sum(1 for mk in mks if mk.pass_flag),
                           fail_count=sum(1 for mk in mks if not mk.pass_flag)))
    session.flush()
    # division rank: position within division, ordered by obtained marks desc
    divs = [session.exec(select(Result).where(Result.exam_id == exam.id,
                                              Result.division == d)).all() for d in (1, 2, 3)]
    for div in divs:
        div.sort(key=lambda r: (-r.total_obtained, r.student_id))
        for rank, r in enumerate(div, start=1):
            r.division_rank = rank
            session.add(r)
    session.commit()
    record(session, actor=user.username, action="update", resource=f"exam#{exam_id}",
           detail={"marks_written": written})
    return {"exam_id": exam_id, "marks_written": written,
            "students_recomputed": len(per_student), "results_recomputed": True}


@router.post("/{exam_id}/publish")
def publish_results(exam_id: int, session: Session = Depends(get_session),
                    user: User = Depends(require_roles("admin"))):
    now = datetime.now(timezone.utc)
    count = 0
    for r in session.exec(select(Result).where(Result.exam_id == exam_id)).all():
        r.published_at = now
        session.add(r)
        count += 1
    session.commit()
    record(session, actor=user.username, action="update", resource=f"exam#{exam_id}",
           detail={"published": count})
    return {"exam_id": exam_id, "published_rows": count, "published_at": str(now)}
