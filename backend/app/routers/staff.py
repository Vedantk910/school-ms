"""Staff HR + light payroll: profiles, leave lifecycle, computed monthly net pay.

Payroll model (D3 - not a full engine): net = base + allowances - deductions
- (approved unpaid-leave days that month, capped at 22) x (base // 22).
All mutations are audit-logged."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.models import User
from app.models.staff import LeaveRecord, PayrollEntry, StaffMember

router = APIRouter(prefix="/staff", tags=["staff"])
WORKING_DAYS = 22


def _rs(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"


class StaffIn(BaseModel):
    staff_code: str
    name: str
    category: str = "teaching"
    designation: str = ""
    joined_date: str  # YYYY-MM-DD
    monthly_base_paise: int = 0
    monthly_allowances_paise: int = 0
    active: bool = True


class LeaveIn(BaseModel):
    leave_type: str = "casual"  # casual | sick | unpaid
    from_date: str
    to_date: str | None = None
    days: int | None = None


class PayrollIn(BaseModel):
    month: str  # 'YYYY-MM'
    deductions_paise: int = 0


@router.get("")
def list_staff(session: Session = Depends(get_session),
               user: User = Depends(require_roles("admin", "teacher"))):
    rows = session.exec(select(StaffMember).where(StaffMember.active == True)).all()  # noqa: E712
    return [{"id": s.id, "staff_code": s.staff_code, "name": s.name,
             "category": s.category, "designation": s.designation,
             "base_rs": _rs(s.monthly_base_paise)} for s in rows]


@router.post("")
def create_staff(body: StaffIn, session: Session = Depends(get_session),
                 user: User = Depends(require_roles("admin"))):
    s = StaffMember(staff_code=body.staff_code, name=body.name, category=body.category,
                    designation=body.designation, joined_date=date.fromisoformat(body.joined_date),
                    monthly_base_paise=body.monthly_base_paise,
                    monthly_allowances_paise=body.monthly_allowances_paise,
                    active=body.active)
    session.add(s)
    session.commit()
    session.refresh(s)
    record(session, actor=user.username, action="create", resource=f"staff#{s.id}",
           detail={"staff_code": body.staff_code})
    return {"id": s.id, "staff_code": s.staff_code}


@router.post("/{staff_id}/leave")
def request_leave(staff_id: int, body: LeaveIn, session: Session = Depends(get_session),
                  user: User = Depends(require_roles("admin", "teacher"))):
    s = session.get(StaffMember, staff_id)
    if s is None:
        raise HTTPException(404, "staff not found")
    if body.leave_type not in ("casual", "sick", "unpaid"):
        raise HTTPException(400, "invalid leave_type")
    fd = date.fromisoformat(body.from_date)
    td = date.fromisoformat(body.to_date) if body.to_date else fd
    days = body.days if body.days is not None else (td - fd).days + 1
    leave = LeaveRecord(staff_id=staff_id, leave_type=body.leave_type, from_date=fd,
                       to_date=td, days=days, applied_date=date(2026, 6, 30))
    session.add(leave)
    session.commit()
    session.refresh(leave)
    record(session, actor=user.username, action="create", resource=f"leave#{leave.id}",
           detail={"staff_id": staff_id, "type": body.leave_type, "days": days})
    return {"leave_id": leave.id, "staff_id": staff_id, "days": days, "status": leave.status}


def _set_leave_status(leave_id: int, status: str, session: Session, user: User):
    leave = session.get(LeaveRecord, leave_id)
    if leave is None:
        raise HTTPException(404, "leave not found")
    leave.status = status
    session.add(leave)
    session.commit()
    record(session, actor=user.username, action="update", resource=f"leave#{leave_id}",
           detail={"status": status})
    return {"leave_id": leave_id, "status": status}


@router.post("/leave/{leave_id}/approve")
def approve_leave(leave_id: int, session: Session = Depends(get_session),
                  user: User = Depends(require_roles("admin"))):
    return _set_leave_status(leave_id, "approved", session, user)


@router.post("/leave/{leave_id}/reject")
def reject_leave(leave_id: int, session: Session = Depends(get_session),
                 user: User = Depends(require_roles("admin"))):
    return _set_leave_status(leave_id, "rejected", session, user)


@router.post("/payroll/calculate")
def calculate_payroll(body: PayrollIn, session: Session = Depends(get_session),
                      user: User = Depends(require_roles("admin"))):
    y, m = body.month.split("-")
    # portable month window (date-range, not LIKE-on-date which Postgres rejects)
    y_i, m_i = int(y), int(m)
    first = date(y_i, m_i, 1)
    nxt = date(y_i + 1, 1, 1) if m_i == 12 else date(y_i, m_i + 1, 1)
    staff = session.exec(select(StaffMember).where(StaffMember.active == True)).all()  # noqa: E712
    for s in staff:
        unpaid_days = 0
        for lv in session.exec(select(LeaveRecord).where(
            LeaveRecord.staff_id == s.id, LeaveRecord.status == "approved",
            LeaveRecord.leave_type == "unpaid",
            LeaveRecord.from_date >= first, LeaveRecord.from_date < nxt)).all():
            unpaid_days += lv.days
        unpaid_days = min(unpaid_days, WORKING_DAYS)
        daily_rate = s.monthly_base_paise // WORKING_DAYS
        deductions = body.deductions_paise + unpaid_days * daily_rate
        net = s.monthly_base_paise + s.monthly_allowances_paise - deductions
        entry = session.exec(select(PayrollEntry).where(
            PayrollEntry.staff_id == s.id, PayrollEntry.month == body.month)).first()
        if entry:
            entry.unpaid_days = unpaid_days
            entry.deductions_paise = deductions
            entry.net_paise = net
            session.add(entry)
        else:
            session.add(PayrollEntry(staff_id=s.id, month=body.month,
                                     base_paise=s.monthly_base_paise,
                                     allowances_paise=s.monthly_allowances_paise,
                                     deductions_paise=deductions,
                                     unpaid_days=unpaid_days, net_paise=net))
    session.commit()
    record(session, actor=user.username, action="create", resource="payroll",
           detail={"month": body.month, "staff_count": len(staff)})
    return {"month": body.month, "entries": _payroll_rows(session, body.month)}


@router.get("/payroll")
def payroll_sheet(month: str = Query(...), session: Session = Depends(get_session),
                  user: User = Depends(require_roles("admin", "teacher"))):
    rows = _payroll_rows(session, month)
    return {"month": month, "entries": rows}


def _payroll_rows(session: Session, month: str) -> list[dict]:
    entries = session.exec(select(PayrollEntry).where(PayrollEntry.month == month)).all()
    names = {s.id: s.name for s in session.exec(select(StaffMember)).all()}
    return [
        {"staff_id": e.staff_id, "staff_name": names.get(e.staff_id, ""),
         "base_rs": _rs(e.base_paise), "allowances_rs": _rs(e.allowances_paise),
         "deductions_rs": _rs(e.deductions_paise), "unpaid_days": e.unpaid_days,
         "net_paise": e.net_paise, "net_rs": _rs(e.net_paise), "status": e.status}
        for e in entries]
