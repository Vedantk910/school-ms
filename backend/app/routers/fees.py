"""Fees & billing: bills, payments, numbered GST receipts, student ledger."""
import json
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select
from sqlalchemy import func

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.models import (
    AcademicYear, Bill, BillLine, FeeHead, Payment, Receipt, ReceiptSequence,
    Student, User,
)

router = APIRouter(prefix="/fees", tags=["fees"])


def _paise_to_rs(p: int) -> str:
    return f"{p // 100}.{p % 100:02d}"


class PaymentIn(BaseModel):
    student_id: int
    year_label: str = "2025-26"
    amount_paise: int
    mode: str = "cash"  # cash | upi | card | cheque
    paid_at: str | None = None  # ISO date; defaults to as-of


@router.post("/payments")
def pay(body: PaymentIn, session: Session = Depends(get_session),
        user: User = Depends(require_roles("admin"))):
    year = session.exec(select(AcademicYear).where(AcademicYear.label == body.year_label)).first()
    if year is None:
        raise HTTPException(404, "academic year not found")
    paid_at = datetime.fromisoformat(body.paid_at) if body.paid_at else None

    # apply against this student's oldest open bills first (simple FIFO)
    bills = session.exec(select(Bill).where(
        Bill.student_id == body.student_id, Bill.year_id == year.id,
        Bill.status.in_(["pending", "partial", "overdue"]),
        Bill.waived == False).order_by(Bill.installment)).all()  # noqa: E712
    remaining = body.amount_paise
    applied = []
    for b in bills:
        if remaining <= 0:
            break
        open_amount = b.total - b.paid
        take = min(remaining, open_amount)
        b.paid += take
        b.status = "paid" if b.paid >= b.total else "partial"
        remaining -= take
        applied.append(b.id)
        session.add(b)
    session.flush()

    pay = Payment(year_id=year.id, student_id=body.student_id,
                  bill_id=applied[0] if applied else None,
                  paid_at=paid_at or datetime.now(timezone.utc),
                  amount=body.amount_paise, mode=body.mode)
    session.add(pay)
    session.flush()

    # issue a numbered receipt (FY sequential, gap-audited)
    fy = year.start_date.year if year.start_date.month >= 4 else year.start_date.year - 1
    seq = session.exec(select(ReceiptSequence).where(ReceiptSequence.fiscal_year == fy)).first()
    if seq is None:
        seq = ReceiptSequence(fiscal_year=fy, last_no=0)
        session.add(seq)
        session.flush()
    seq.last_no += 1
    receipt_no = f"FY{fy}/{seq.last_no:06d}"
    receipt = Receipt(receipt_no=receipt_no, fiscal_year=fy, year_id=year.id,
                      payment_ids=json.dumps([pay.id]), student_id=body.student_id,
                      total=body.amount_paise,
                      issued_at=paid_at or datetime.now(timezone.utc))
    session.add(receipt)
    pay.receipt_no = receipt_no
    session.add(pay)
    session.commit()
    record(session, actor=user.username, action="create", resource=f"payment#{pay.id}",
           detail={"receipt_no": receipt_no, "amount": body.amount_paise,
                   "applied_to": applied})
    return {"payment_id": pay.id, "receipt_no": receipt_no, "applied_to_bills": applied,
            "amount_paise": body.amount_paise, "amount_rs": _paise_to_rs(body.amount_paise)}


@router.get("/student-ledger/{student_id}")
def student_ledger(student_id: int, year_label: str = Query("2025-26"),
                   session: Session = Depends(get_session),
                   user: User = Depends(require_roles("admin", "teacher", "parent"))):
    year = session.exec(select(AcademicYear).where(AcademicYear.label == year_label)).first()
    bills = session.exec(select(Bill).where(Bill.student_id == student_id,
                                            Bill.year_id == year.id)).all()
    total_due = sum(b.total for b in bills if not b.waived)
    total_paid = sum(b.paid for b in bills)
    outstanding = total_due - total_paid
    return {
        "student_id": student_id, "year": year_label,
        "bills": [
            {"installment": b.installment, "status": b.status, "due": str(b.due_date),
             "total_rs": _paise_to_rs(b.total), "paid_rs": _paise_to_rs(b.paid),
             "waived": b.waived, "waiver_reason": b.waiver_reason}
            for b in sorted(bills, key=lambda x: x.installment)
        ],
        "totals": {"due": total_due, "paid": total_paid, "outstanding": outstanding,
                   "due_rs": _paise_to_rs(total_due), "outstanding_rs": _paise_to_rs(outstanding)},
    }


@router.get("/receipt/{receipt_no}")
def receipt_view(receipt_no: str, session: Session = Depends(get_session),
                 user: User = Depends(require_roles("admin", "teacher", "parent"))):
    r = session.exec(select(Receipt).where(Receipt.receipt_no == receipt_no)).first()
    if r is None:
        raise HTTPException(404, "receipt not found")
    pays = [p for p in session.exec(select(Payment).where(Payment.receipt_no == receipt_no)).all()]
    lines: list[dict] = []
    for p in pays:
        for b in session.exec(select(Bill).where(Bill.id == p.bill_id)).all():
            for l in session.exec(select(BillLine).where(BillLine.bill_id == b.id)).all():
                fh = session.exec(select(FeeHead).where(FeeHead.id == l.fee_head_id)).first()
                lines.append({"head": fh.name if fh else "?", "amount_rs": _paise_to_rs(l.amount),
                              "gst_rs": _paise_to_rs(l.gst), "gst_rate": fh.gst_rate})
    return {
        "receipt_no": r.receipt_no, "fiscal_year": r.fiscal_year,
        "student_id": r.student_id, "issued_at": str(r.issued_at),
        "total_rs": _paise_to_rs(r.total), "lines": lines,
        "note": "Printable GST-format receipt (demo). GST on tuition exempt for education.",
    }


@router.get("/receipts/gap-audit")
def receipt_gap_audit(fiscal_year: int = Query(2025),
                      session: Session = Depends(get_session),
                      user: User = Depends(require_roles("admin"))):
    """Finance-grade detail: verify receipt numbering is gap-free within a FY."""
    rows = session.exec(select(Receipt.receipt_no).where(Receipt.fiscal_year == fiscal_year)).all()
    nums = sorted(int(r.split("/")[1]) for r in rows)
    gaps = []
    for a, b in zip(nums, nums[1:]):
        if b - a > 1:
            gaps.append({"after": a, "before": b})
    last = session.exec(select(ReceiptSequence).where(
        ReceiptSequence.fiscal_year == fiscal_year)).first()
    return {"fiscal_year": fiscal_year, "issued": len(nums),
            "expected": last.last_no if last else 0,
            "gaps": gaps, "ok": not gaps and len(nums) == (last.last_no if last else 0)}
