"""Comms gateway control: drain the outbox through the configured provider.

Admin-only. The provider is selected by SCHOOLMS_COMMS_BACKEND (log | sms).
Drain is consent-gated and can be cost-capped per batch."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlmodel import Session

from app.comms import drain_outbox, get_comms_provider
from app.db import get_session
from app.dependencies import require_roles
from app.models import User

router = APIRouter(prefix="/comms", tags=["comms"])


class DrainIn(BaseModel):
    cost_cap_paise: int | None = None  # None = uncapped


@router.get("/status")
def provider_status(session: Session = Depends(get_session),
                    user: User = Depends(require_roles("admin", "teacher"))):
    p = get_comms_provider()
    return {"backend": p.name,
            "per_message_cost_paise": getattr(p, "cost_paise", 0),
            "note": "log backend is offline/zero-cost; set SCHOOLMS_COMMS_BACKEND=sms "
                    "+ SCHOOLMS_SMS_BASE_URL to dispatch for real"}


@router.post("/drain")
def drain(body: DrainIn | None = None, session: Session = Depends(get_session),
          user: User = Depends(require_roles("admin"))):
    provider = get_comms_provider()
    cap = body.cost_cap_paise if body else None
    out = drain_outbox(session, provider, cost_cap_paise=cap)
    out["actor"] = user.username
    return out
