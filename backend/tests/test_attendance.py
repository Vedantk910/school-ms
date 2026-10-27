"""Attendance: register entry + summary."""
from tests.conftest import _auth


def test_register_requires_teacher_or_admin(client, parent_token):
    r = client.post("/api/v1/attendance/register",
                    json={"section": "6A", "d": "2025-04-01",
                          "entries": [[1, "P"]]},
                    headers=_auth(parent_token["access_token"]))
    assert r.status_code == 403


def test_register_attendance(client, teacher_token):
    r = client.post("/api/v1/attendance/register",
                    json={"section": "6A", "d": "2025-04-01",
                          "entries": [[1, "P"], [2, "A"]]},
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 200
    assert r.json()["written"] >= 0


def test_register_rejects_bad_type(client, teacher_token):
    r = client.post("/api/v1/attendance/register",
                    json={"section": "6A", "d": "2025-04-01",
                          "entries": [[1, "X"]]},
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 400


def test_attendance_summary(client, teacher_token):
    r = client.get("/api/v1/attendance/summary",
                   headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 200
    body = r.json()
    for k in ("total", "present", "absent", "present_pct"):
        assert k in body
