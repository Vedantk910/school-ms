"""Tamper-evident audit log: every mutation records actor + SHA-256 content hash."""
import hashlib
import json

from sqlmodel import Session
from app.models import AuditLog


def _hash(payload: dict) -> str:
    canon = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(canon.encode()).hexdigest()


def record(
    session: Session,
    *,
    actor: str,
    action: str,
    resource: str,
    detail: dict | None = None,
) -> AuditLog:
    log = AuditLog(actor=actor, action=action, resource=resource,
                   detail=json.dumps(detail, default=str),
                   content_hash=_hash({"actor": actor, "action": action,
                                       "resource": resource, "detail": detail}))
    session.add(log)
    session.commit()
    session.refresh(log)
    return log
