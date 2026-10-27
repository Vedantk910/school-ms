"""Audit log: who touched what, with a before/after content hash."""
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel
from sqlalchemy import Column, DateTime, String, Text

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base, table=True):
    __tablename__ = "audit_log"
    id: int | None = Field(default=None, primary_key=True)
    actor: str = Field(index=True, default="system")  # username or "system"
    action: str = Field(index=True)  # create | update | delete | login | export
    resource: str = Field(default="")  # e.g. "student#123"
    detail: str = Field(default="", sa_column=Column(Text))
    content_hash: str = Field(default="")  # sha1 of before/after for tamper-evidence
    created_at: datetime = Field(default_factory=_utcnow, index=True)
