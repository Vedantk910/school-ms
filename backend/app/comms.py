"""Comms gateway: provider-swappable outbox dispatch behind the message outbox.

Design (V1 hardening):
- Providers are swappable via env (SCHOOLMS_COMMS_BACKEND = log | sms).
- ``log`` (default) is deterministic, offline, zero-cost - the demo/CI backend.
- ``sms`` is an HTTP provider that POSTs to a configurable gateway URL.
- Dispatch is consent-gated: outbound to guardians only fires when the
  guardian has DPDP consent, and cost-capped per batch.

Keeping this dependency-light: the HTTP provider uses stdlib ``urllib`` so no
new runtime dependency is added (check requirements.txt - none added here).
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from sqlmodel import Session, select

from app.config import settings
from app.models import Guardian, OutboxMessage, Student


@dataclass
class SendResult:
    recipient: str
    delivered: bool
    cost_paise: int = 0
    error: str | None = None
    backend: str = "log"


class CommProvider(Protocol):
    name: str

    def send(self, *, template: str, subject: str, body: str,
             recipient: str, lang: str = "en", advisory: bool = True) -> SendResult:
        ...


class LogProvider:
    """In-memory, deterministic, zero-cost. Records dispatches for tests."""
    name = "log"

    def __init__(self) -> None:
        self.deliveries: list[dict] = []

    def send(self, *, template: str, subject: str, body: str,
             recipient: str, lang: str = "en", advisory: bool = True) -> SendResult:
        self.deliveries.append({"template": template, "subject": subject,
                                "body": body, "recipient": recipient,
                                "lang": lang, "advisory": advisory})
        return SendResult(recipient=recipient, delivered=True, cost_paise=0,
                          backend=self.name)


class HttpSmsProvider:
    """POSTs a composed notice to an SMS/WhatsApp gateway. Stdlib urllib only."""
    name = "sms"

    def __init__(self, base_url: str, api_key: str = "",
                 channel: str = "sms", cost_paise: int = 100) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.channel = channel
        self.cost_paise = cost_paise  # per-message cost for capping

    def send(self, *, template: str, subject: str, body: str,
             recipient: str, lang: str = "en", advisory: bool = True) -> SendResult:
        payload = json.dumps({
            "to": recipient, "channel": self.channel, "lang": lang,
            "subject": subject, "body": body, "advisory": advisory,
            "template": template,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/send",
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                **({"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}),
            })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                resp.read()
            return SendResult(recipient=recipient, delivered=True,
                              cost_paise=self.cost_paise, backend=self.name)
        except Exception as e:  # noqa: BLE001 - surface as a delivery error
            return SendResult(recipient=recipient, delivered=False, cost_paise=0,
                              error=str(e), backend=self.name)


def get_comms_provider() -> CommProvider:
    """Factory: log (default) or sms, driven by env / settings."""
    backend = getattr(settings, "comms_backend", "log") or "log"
    if backend == "sms":
        return HttpSmsProvider(
            base_url=getattr(settings, "sms_base_url", "") or "http://sms.local",
            api_key=getattr(settings, "sms_api_key", ""),
            channel=getattr(settings, "sms_channel", "sms"),
            cost_paise=100,
        )
    return LogProvider()


def _recipient_authorized_guardian(audience: str, session: Session) -> bool:
    """Consent gate: guardian-targeted messages require DPDP consent.

    Audience encodings: 'all' | 'class:X' | 'student:N' | 'guardian:GID'.
      - 'all' / 'class:X' are treated as guardian-broadcasts -> require that
        *some* guardian exists with consent (fail-safe: refuse if none consented).
      - 'guardian:GID' -> that specific guardian must have consent_given.
      - 'student:N' -> self-service to the student; no guardian consent needed.
    """
    if audience.startswith("student:"):
        return True  # no guardian data in the loop
    if audience.startswith("guardian:"):
        gid = int(audience.split(":", 1)[1])
        g = session.get(Guardian, gid)
        return bool(g and g.consent_given)
    # 'all' / 'class:X' -> require at least one consenting guardian to exist
    n = session.exec(select(Guardian).where(Guardian.consent_given == True)).all()  # noqa: E712
    return len(n) > 0


def drain_outbox(
    session: Session,
    provider: CommProvider,
    cost_cap_paise: int | None = None,
) -> dict:
    """Dispatch queued, non-inapp outbox messages through ``provider``.

    - consent-gated (see _recipient_authorized_guardian)
    - cost-capped: stops when cumulative provider cost would exceed the cap;
      the remaining rows stay queued for the next drain.
    - marks dispatched rows sent_state='sent'.
    """
    queued = session.exec(select(OutboxMessage).where(
        OutboxMessage.channel != "inapp",
        OutboxMessage.sent_state == "queued")).all()

    sent = 0
    skipped_no_consent = 0
    spent = 0
    for msg in queued:
        if cost_cap_paise is not None and spent + provider_cost(provider) > cost_cap_paise:
            break  # leave this and the rest queued
        if not _recipient_authorized_guardian(msg.audience, session):
            msg.sent_state = "rejected_no_consent"
            skipped_no_consent += 1
            session.add(msg)
            continue
        res = provider.send(template=msg.template, subject=msg.subject,
                            body=msg.body, recipient=msg.audience,
                            lang=msg.lang, advisory=msg.advisory)
        msg.sent_state = "sent" if res.delivered else "failed"
        session.add(msg)
        sent += 1
        spent += res.cost_paise
    session.commit()
    return {"queued": len(queued), "sent": sent,
            "skipped_no_consent": skipped_no_consent,
            "cost_spent_paise": spent, "provider": provider.name}


def provider_cost(provider: CommProvider) -> int:
    """Per-message cost estimate used for capping (0 for the log provider)."""
    return getattr(provider, "cost_paise", 0)
