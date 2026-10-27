"""Events & activities: create (admin), list, participation upsert, summary math."""
from tests.conftest import _auth

BASE = "/api/v1/events"


def _create_event(client, token, **overrides):
    body = {"name": "Annual Sports Day", "kind": "sports",
            "event_date": "2025-12-01", "is_mandatory": True}
    body.update(overrides)
    r = client.post(BASE, json=body, headers=_auth(token))
    assert r.status_code == 200, r.text
    return r.json()


def test_create_event_admin(client, admin_token):
    ev = _create_event(client, admin_token["access_token"])
    assert ev["name"] == "Annual Sports Day"
    assert ev["kind"] == "sports"
    assert ev["is_mandatory"] is True
    assert ev["year_label"] == "2025-26"


def test_list_events_any_role(client, admin_token, teacher_token):
    ev = _create_event(client, admin_token["access_token"])
    # a teacher (non-admin authenticated role) can list
    r = client.get(f"{BASE}?year_label=2025-26", headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 200
    listing = {e["id"]: e for e in r.json()}
    assert listing[ev["id"]]["name"] == ev["name"]
    assert listing[ev["id"]]["participation_count"] == 0


def test_create_event_teacher_forbidden(client, teacher_token):
    r = client.post(BASE, json={"name": "Club Meet", "kind": "meeting",
                                "event_date": "2025-12-05"},
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 403


def test_participate_upsert_idempotent(client, teacher_token, admin_token):
    ev = _create_event(client, admin_token["access_token"])
    body = [
        {"student_id": 1, "attended": True},
        {"student_id": 2, "attended": False, "remark": "on leave"},
        {"student_id": 3, "attended": True},
    ]
    r = client.post(f"{BASE}/{ev['id']}/participate", json=body,
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 200
    assert r.json()["written"] == 3
    count = _participation_count(client, admin_token, ev["id"])
    assert count == 3
    # second call with the same body must not add rows
    r2 = client.post(f"{BASE}/{ev['id']}/participate", json=body,
                     headers=_auth(teacher_token["access_token"]))
    assert r2.status_code == 200
    assert _participation_count(client, admin_token, ev["id"]) == 3


def _participation_count(client, admin_token, event_id):
    r = client.get(f"{BASE}?year_label=2025-26",
                   headers=_auth(admin_token["access_token"]))
    return next(e["participation_count"] for e in r.json() if e["id"] == event_id)


def test_summary_math(client, teacher_token, admin_token):
    ev = _create_event(client, admin_token["access_token"])
    body = [
        {"student_id": 1, "attended": True},
        {"student_id": 2, "attended": False, "remark": "sick"},
        {"student_id": 3, "attended": False},
    ]
    r = client.post(f"{BASE}/{ev['id']}/participate", json=body,
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 200
    s = client.get(f"{BASE}/{ev['id']}/summary",
                   headers=_auth(teacher_token["access_token"]))
    assert s.status_code == 200
    out = s.json()
    assert out["recorded"] == 3
    assert out["attended"] == 1
    assert out["absent"] == 2
    assert [m["student_id"] for m in out["mandatory_not_attended"]] == [2, 3]


def test_summary_non_mandatory_no_missing(client, teacher_token, admin_token):
    ev = _create_event(client, admin_token["access_token"], is_mandatory=False,
                       name="Cultural Night", kind="cultural")
    body = [{"student_id": 1, "attended": True},
            {"student_id": 2, "attended": False}]
    client.post(f"{BASE}/{ev['id']}/participate", json=body,
                headers=_auth(teacher_token["access_token"]))
    out = client.get(f"{BASE}/{ev['id']}/summary",
                    headers=_auth(teacher_token["access_token"])).json()
    assert out["absent"] == 1
    assert out["mandatory_not_attended"] == []
