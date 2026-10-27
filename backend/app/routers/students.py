"""Students & admissions: list/detail, admission funnel, DPDP consent, guardian portal view."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from sqlalchemy import func

from app.audit import record
from app.db import get_session
from app.dependencies import current_user, require_roles
from app.models import (
    AcademicYear, Admission, Attendance, Bill, Enrollment, Exam, Insight,
    Result, Student, User,
)

router = APIRouter(prefix="/students", tags=["students"])


def _student_out(s: Student, session: Session) -> dict:
    year = session.exec(select(AcademicYear).where(AcademicYear.label == "2025-26")).first()
    enr = session.exec(select(Admission).where(Admission.student_id == s.id,
                                                Admission.year_id == year.id)).first()
    bills = session.exec(select(Bill).where(Bill.student_id == s.id, Bill.status.in_(
        ["pending", "partial", "overdue"]))).all()
    due = sum(b.total - b.paid for b in bills)
    insights = session.exec(select(Insight).where(Insight.student_id == s.id)).all()
    return {
        "id": s.id, "admission_no": s.admission_no, "name": s.name,
        "gender": s.gender, "dob": str(s.date_of_birth), "active": s.active,
        "uin": s.uin_id, "aadhaar_masked": s.aadhaar_masked,
        "rte_ews": bool(enr and enr.rte_ews),
        "consent_given": bool(s.guardian_ids),  # populated when guardian linked
        "outstanding_paise": due,
        "open_bills": len([b for b in bills if b.status in ("pending", "partial", "overdue")]),
        "insights": [
            {"kind": i.kind, "score": round(i.score, 4), "label": i.label,
             "reasons": i.reasons_json, "model": f"{i.model_name} v{i.model_version}"}
            for i in insights
        ],
    }


@router.get("")
def list_students(
    q: str = Query(default="", max_length=100),
    active: bool = Query(default=True),
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
    user: User = Depends(require_roles("admin", "teacher")),
):
    stmt = select(Student)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Student.name.like(like)) | (Student.admission_no.like(like)))
    if active:
        stmt = stmt.where(Student.active == True)  # noqa: E712
    total = session.exec(select(func.count()).select_from(stmt.subquery())).one()
    rows = session.exec(stmt.offset(offset).limit(limit)).all()
    return {"total": total, "students": [_student_out(s, session) for s in rows]}


@router.get("/{student_id}")
def student_detail(
    student_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(current_user),
):
    s = session.get(Student, student_id)
    if s is None:
        raise HTTPException(404, "student not found")
    # RBAC: parent may view only their linked child; student only themselves
    if user.role == "parent" and user.student_id != student_id:
        raise HTTPException(403, "not your child")
    if user.role == "student" and user.student_id != student_id:
        raise HTTPException(403, "not yourself")

    out = _student_out(s, session)
    year = session.exec(select(AcademicYear).where(AcademicYear.label == "2025-26")).first()
    # exam history (last exam per exam id for this student)
    results = session.exec(select(Result).where(Result.student_id == student_id).join(
        Exam, Exam.id == Result.exam_id)).all()
    out["exam_history"] = [
        {"exam_id": r.exam_id, "pct": r.percentage, "division": r.division,
         "grade": r.overall_grade, "pass": r.pass_count, "fail": r.fail_count}
        for r in results[-4:]
    ]
    # attendance summary for current year (Attendance links via Enrollment)
    enr_ids = [e.id for e in session.exec(select(Enrollment).where(
        Enrollment.student_id == student_id, Enrollment.year_id == year.id)).all()]
    att_total = session.exec(select(func.count(Attendance.id)).where(
        Attendance.enrollment_id.in_(enr_ids), Attendance.type == "P")).one()
    att_days = session.exec(select(func.count(Attendance.id)).where(
        Attendance.enrollment_id.in_(enr_ids))).one()
    pct = round(100 * att_total / att_days, 1) if att_days else 0.0
    out["attendance_pct"] = pct
    out["attendance_present"] = att_total
    out["attendance_days"] = att_days
    return out


@router.get("/{student_id}/admissions")
def admission_history(student_id: int, session: Session = Depends(get_session),
                     user: User = Depends(require_roles("admin"))):
    rows = session.exec(select(Admission).where(Admission.student_id == student_id)).all()
    return [{"year_id": r.year_id, "stage": r.stage, "rte_ews": r.rte_ews,
             "admission_date": str(r.admission_date)} for r in rows]


@router.post("/consent")
def record_guardian_consent(
    student_id: int,
    grant: bool = True,
    session: Session = Depends(get_session),
    user: User = Depends(require_roles("admin", "parent")),
):
    s = session.get(Student, student_id)
    if s is None:
        raise HTTPException(404, "student not found")
    record(session, actor=user.username, action="update", resource=f"student#{student_id}",
           detail={"consent": "granted" if grant else "revoked"})
    return {"student_id": student_id, "consent_given": grant,
            "note": "DPDP 2023: minor data processed only with guardian consent"}
