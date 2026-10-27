"""Admin: role dashboards, audit log, receipt gap audit, system stats."""
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from sqlalchemy import func

from app.db import get_session
from app.dependencies import require_roles
from app.models import (
    AcademicYear, Attendance, AuditLog, Bill, Enrollment, Insight,
    ModelRegistry, Student,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboards/overview")
def overview(session: Session = Depends(get_session),
             user: "object" = Depends(require_roles("admin", "teacher", "parent"))):
    year = session.exec(select(AcademicYear).where(AcademicYear.label == "2025-26")).first()
    students = session.exec(select(func.count(Student.id)).where(Student.active == True)).one()  # noqa: E712
    enr = session.exec(select(func.count(Enrollment.id)).where(Enrollment.year_id == year.id,
                                                                 Enrollment.status == "active")).one()

    att_total = session.exec(select(func.count(Attendance.id))).one()
    att_p = session.exec(select(func.count(Attendance.id)).where(Attendance.type == "P")).one()

    bills = session.exec(select(Bill).where(Bill.year_id == year.id)).all()
    due = sum(b.total for b in bills if not b.waived)
    paid = sum(b.paid for b in bills)
    overdue = sum(b.total - b.paid for b in bills
                   if b.due_date.isoformat() < "2026-06-30" and b.status in ("pending", "partial", "overdue") and not b.waived)

    ar = session.exec(select(func.count(Insight.id)).where(
        Insight.kind == "at_risk", Insight.label == True)).one()  # noqa: E712
    fd = session.exec(select(func.count(Insight.id)).where(
        Insight.kind == "fee_default", Insight.label == True)).one()  # noqa: E712
    models = session.exec(select(func.count(ModelRegistry.id))).one()

    return {
        "academic_year": "2025-26",
        "students_active": students,
        "enrollments": enr,
        "attendance_pct": round(100 * att_p / att_total, 1) if att_total else 0.0,
        "fees": {"billed_rs": due // 100, "collected_rs": paid // 100,
                 "collection_pct": round(100 * paid / due, 1) if due else 0.0,
                 "outstanding_rs": max(0, due - paid) // 100},
        "ml": {"at_risk_flags": ar, "fee_default_flags": fd, "models_trained": models},
    }


@router.get("/audit")
def audit(action: str = Query(default=""), limit: int = Query(default=50, le=500),
          session: Session = Depends(get_session),
          user: "object" = Depends(require_roles("admin"))):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = session.exec(stmt.order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [{"actor": r.actor, "action": r.action, "resource": r.resource,
             "content_hash": r.content_hash, "created_at": str(r.created_at)} for r in rows]
