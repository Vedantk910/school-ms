"""Fees: heads, installment-aware billing, payments, numbered GST receipts, ledger."""
from datetime import date, datetime, timezone

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, Date, DateTime, String, Text, Float, Integer, UniqueConstraint, ForeignKey

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeeHead(Base, table=True):
    """A billable category with a GST rate. e.g. Tuition, Exam Fee, Transport, PTA Levy."""
    __tablename__ = "fee_head"
    id: int | None = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    gst_rate: int = Field(default=0)  # whole percent; 0 for education (tuition)


class Bill(Base, table=True):
    """A student's bill for one installment of an academic year. Amounts are paise."""
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    installment: int = Field(index=True, default=1)  # 1..N within year
    due_date: date = Column(Date, nullable=False)
    status: str = Field(index=True, default="pending")  # pending | partial | paid | overdue
    waived: bool = Field(default=False)
    waiver_reason: str | None = Column(Text, nullable=True)
    # paise
    principal: int = Field(default=0)
    gst: int = Field(default=0)
    total: int = Field(default=0)
    paid: int = Field(default=0)


class BillLine(Base, table=True):
    """Itemization of a bill by fee head (for the receipt)."""
    __tablename__ = "bill_line"
    id: int | None = Field(default=None, primary_key=True)
    bill_id: int = Field(foreign_key="bill.id", index=True)
    fee_head_id: int = Field(foreign_key="fee_head.id", index=True)
    amount: int  # paise
    gst: int = Field(default=0)  # paise


class Payment(Base, table=True):
    id: int | None = Field(default=None, primary_key=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    student_id: int = Field(foreign_key="student.id", index=True)
    bill_id: int | None = Field(default=None, foreign_key="bill.id", index=True)
    paid_at: datetime = Field(default_factory=_utcnow, index=True)
    amount: int = Field(default=0)  # paise
    mode: str = Field(default="cash")  # cash | upi | card | cheque
    receipt_no: str | None = Field(default=None, index=True)


class Receipt(Base, table=True):
    """Sequential, gap-audited, GST-formatted receipt (finance-grade detail)."""
    id: int | None = Field(default=None, primary_key=True)
    receipt_no: str = Field(index=True, unique=True)  # FY2025/000001
    fiscal_year: int = Field(index=True)
    year_id: int = Field(foreign_key="academic_year.id", index=True)
    # JSON-encoded list of payment ids (SQLite can't bind a Python list)
    payment_ids: str = Field(default="[]", sa_column=Column(Text, default="[]"))
    student_id: int = Field(foreign_key="student.id", index=True)
    issued_at: datetime = Field(default_factory=_utcnow)
    total: int = Field(default=0)  # paise
    gst_total: int = Field(default=0)  # paise
    line_count: int = Field(default=0)


class ReceiptSequence(Base, table=True):
    """Per-fiscal-year counter enabling gap-free, audited numbering."""
    __tablename__ = "receipt_sequence"
    fiscal_year: int = Field(primary_key=True)
    last_no: int = Field(default=0)


class ModelRegistry(Base, table=True):
    """Trained ML artifacts: name, version, metrics, artifact path, training split."""
    __tablename__ = "model_registry"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # at_risk | fee_default
    version: int = Field(default=1)
    artifact_path: str
    # JSON-encoded text (serializable dict)
    metrics_json: str = Field(default="{}", sa_column=Column(Text, default="{}"))
    train_years: str = Field(default="")
    eval_years: str = Field(default="")
    trained_at: datetime = Field(default_factory=_utcnow)


class Insight(Base, table=True):
    """An explainable ML insight (at-risk / fee default) with SHAP top-k reasons."""
    id: int | None = Field(default=None, primary_key=True)
    scope: str = Field(index=True, default="student")  # student | class
    student_id: int | None = Field(default=None, index=True)
    kind: str = Field(index=True)  # at_risk | fee_default
    score: float
    label: bool  # model's predicted positive
    # JSON-encoded list of {"feature","value","shap","direction"}
    reasons_json: str = Field(default="[]", sa_column=Column(Text, default="[]"))
    model_name: str
    model_version: int
    created_at: datetime = Field(default_factory=_utcnow)


class OutboxMessage(Base, table=True):
    """Composed notice (in-app / log-mode). channel=log keeps demo cost at zero."""
    __tablename__ = "outbox_message"
    id: int | None = Field(default=None, primary_key=True)
    template: str
    audience: str  # all | class:7A | student:123 | guardian:5
    channel: str = Field(default="inapp")  # inapp | log | sms | whatsapp
    lang: str = Field(default="en")
    subject: str
    body: str
    advisory: bool = Field(default=True)  # LLM-produced content carries this flag
    sent_state: str = Field(default="queued")  # queued | sent | delivered
    created_at: datetime = Field(default_factory=_utcnow)
