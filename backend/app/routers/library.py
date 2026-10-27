"""Library: catalogue search, checkout/return with copy availability, daily late fine.

Fine model: FINE_PER_DAY_PAISE per calendar day past due, computed on return.
Default "today" for a return is the app as-of date (2026-06-30)."""
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.models import Student, User
from app.models.library import Book, Loan

router = APIRouter(prefix="/library", tags=["library"])

FINE_PER_DAY_PAISE = 2000
AS_OF = date(2026, 6, 30)


def _rs(paise: int) -> str:
    return f"{paise // 100}.{paise % 100:02d}"


class CheckoutIn(BaseModel):
    student_id: int
    book_code: str
    due_days: int = 21


@router.get("/books")
def search_books(q: str = Query(default=""),
                 session: Session = Depends(get_session),
                 user: User = Depends(require_roles("admin", "teacher", "parent", "student"))):
    stmt = select(Book)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Book.title.ilike(like)) | (Book.code.ilike(like)))
    rows = session.exec(stmt.limit(50)).all()
    return [{"id": b.id, "code": b.code, "title": b.title, "author": b.author,
             "category": b.category, "total_copies": b.total_copies,
             "available_copies": b.available_copies} for b in rows]


@router.post("/books/checkout")
def checkout(body: CheckoutIn, session: Session = Depends(get_session),
             user: User = Depends(require_roles("admin", "teacher"))):
    book = session.exec(select(Book).where(Book.code == body.book_code)).first()
    if book is None:
        raise HTTPException(404, "book not found")
    if book.available_copies <= 0:
        raise HTTPException(400, "no copies available")
    open_loan = session.exec(select(Loan).where(
        Loan.student_id == body.student_id, Loan.book_id == book.id,
        Loan.status == "issued")).first()
    if open_loan:
        raise HTTPException(400, "student already has an active loan of this book")
    book.available_copies -= 1
    session.add(book)
    issued = AS_OF
    loan = Loan(book_id=book.id, student_id=body.student_id, issued_date=issued,
                due_date=date.fromordinal(issued.toordinal() + body.due_days), status="issued")
    session.add(loan)
    session.commit()
    session.refresh(loan)
    record(session, actor=user.username, action="create", resource=f"loan#{loan.id}",
           detail={"book_code": body.book_code, "student_id": body.student_id,
                   "due_date": str(loan.due_date)})
    return {"loan_id": loan.id, "book_code": book.code, "due_date": str(loan.due_date),
            "fine_policy": f"{FINE_PER_DAY_PAISE} paise/day late"}


@router.post("/loans/{loan_id}/return")
def return_loan(loan_id: int, return_date: str | None = Query(default=None),
                session: Session = Depends(get_session),
                user: User = Depends(require_roles("admin", "teacher"))):
    loan = session.get(Loan, loan_id)
    if loan is None:
        raise HTTPException(404, "loan not found")
    if loan.status == "returned":
        raise HTTPException(400, "loan already returned")
    rd = date.fromisoformat(return_date) if return_date else AS_OF
    days_late = max(0, (rd - loan.due_date).days)
    loan.fine_paise = days_late * FINE_PER_DAY_PAISE
    loan.returned_date = rd
    loan.status = "returned"
    book = session.get(Book, loan.book_id)
    if book is not None:
        book.available_copies += 1
        session.add(book)
    session.add(loan)
    session.commit()
    record(session, actor=user.username, action="update", resource=f"loan#{loan.id}",
           detail={"returned": str(rd), "fine_paise": loan.fine_paise})
    return {"loan_id": loan.id, "returned_date": str(rd), "fine_paise": loan.fine_paise,
            "fine_rs": _rs(loan.fine_paise)}


@router.get("/loans")
def my_loans(student_id: int = Query(default=0),
             session: Session = Depends(get_session),
             user: User = Depends(require_roles("admin", "teacher", "parent", "student"))):
    if user.role in ("parent", "student") and student_id != user.student_id:
        raise HTTPException(403, "can only view your own loans")
    target = student_id or (user.student_id or 0)
    rows = session.exec(select(Loan).where(Loan.student_id == target)).all()
    books = {b.id: b for b in session.exec(select(Book)).all()}
    return [{"loan_id": l.id, "book_code": books[l.book_id].code if l.book_id in books else "?",
             "book_title": books[l.book_id].title if l.book_id in books else "?",
             "status": l.status, "due_date": str(l.due_date),
             "returned_date": str(l.returned_date) if l.returned_date else None,
             "fine_paise": l.fine_paise, "fine_rs": _rs(l.fine_paise)} for l in rows]
