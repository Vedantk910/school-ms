"""Comms gateway: provider selection, consent-gated outbox drain, cost cap.

Tests exercise the pure logic (LogProvider + drain_outbox) and the provider
status endpoint. The HTTP provider's transport is exercised via a fake.
"""
from datetime import date

from app.comms import (
    HttpSmsProvider, LogProvider, drain_outbox, get_comms_provider,
)
from app.db import engine
from app.models import Guardian, OutboxMessage
from sqlmodel import Session, select
from tests.conftest import _auth


def _queued(channel: str, audience: str, template: str = "notice") -> None:
    with Session(engine) as s:
        s.add(OutboxMessage(template=template, audience=audience, channel=channel,
                            lang="en", subject="S", body="B", sent_state="queued"))
        s.commit()


def test_log_provider_records_and_zero_cost():
    p = LogProvider()
    r = p.send(template="t", subject="s", body="b", recipient="guardian:1")
    assert r.delivered and r.cost_paise == 0 and len(p.deliveries) == 1


def test_default_provider_is_log_offline():
    p = get_comms_provider()
    assert p.name == "log"  # demo default - no network, zero cost


def test_http_provider_posts_and_costs():
    p = HttpSmsProvider(base_url="http://sms.local", api_key="k", cost_paise=150)
    # monkeypatch the transport so no real network is hit
    import urllib.request
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = req.data
        class _R:
            def read(self):
                return b"ok"
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
        return _R()

    orig = urllib.request.urlopen
    urllib.request.urlopen = fake_urlopen
    try:
        r = p.send(template="t", subject="s", body="b", recipient="guardian:9")
    finally:
        urllib.request.urlopen = orig
    assert r.delivered and r.cost_paise == 150
    assert captured["url"].endswith("/send")
    import json
    assert json.loads(captured["body"])["to"] == "guardian:9"


def test_drain_dispatches_queued_log_channel(client):
    _queued("log", "all")
    _queued("sms", "all")
    _queued("inapp", "all")  # must be skipped - inapp is not a gateway channel
    p = LogProvider()
    with Session(engine) as s:
        out = drain_outbox(s, p)
    assert out["provider"] == "log"
    # two non-inapp queued rows dispatched
    assert out["sent"] == 2
    with Session(engine) as s:
        sent = s.exec(select(OutboxMessage).where(OutboxMessage.sent_state == "sent")).all()
        assert len(sent) == 2


def test_consent_gate_rejects_no_consent_audience(client):
    # 'all' requires at least one consenting guardian; wipe consent to force reject
    with Session(engine) as s:
        for g in s.exec(select(Guardian)).all():
            g.consent_given = False
            s.add(g)
        s.commit()
    _queued("log", "all")
    with Session(engine) as s:
        out = drain_outbox(s, LogProvider())
        assert out["skipped_no_consent"] == 1
        assert out["sent"] == 0
        rej = s.exec(select(OutboxMessage).where(
            OutboxMessage.sent_state == "rejected_no_consent")).all()
        assert len(rej) == 1


def test_cost_cap_stops_batch_leaves_rest_queued(client):
    class CostedProvider:
        """A delivered provider with a per-message cost, for cap tests."""
        name = "costed"
        cost_paise = 100

        def __init__(self):
            self.deliveries = []

        def send(self, *, template, subject, body, recipient, lang="en", advisory=True):
            self.deliveries.append(recipient)
            from app.comms import SendResult
            return SendResult(recipient=recipient, delivered=True,
                              cost_paise=self.cost_paise, backend=self.name)

    with Session(engine) as s:
        for g in s.exec(select(Guardian)).all():
            g.consent_given = True
            s.add(g)
    # three sms messages, each costs 100 paise; cap at 200 -> only 2 sent
    for _ in range(3):
        _queued("sms", "all")
    with Session(engine) as s:
        out = drain_outbox(s, CostedProvider(), cost_cap_paise=200)
    assert out["sent"] == 2
    assert out["cost_spent_paise"] == 200
    with Session(engine) as s:
        still_queued = s.exec(select(OutboxMessage).where(
            OutboxMessage.sent_state == "queued")).all()
        assert len(still_queued) == 1  # the third stays for a later drain


def test_comms_status_endpoint(client, admin_token):
    r = client.get("/api/v1/comms/status", headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    assert r.json()["backend"] in ("log", "sms")
