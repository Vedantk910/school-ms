"""Admin: dashboard overview + audit log."""
from tests.conftest import _auth


def test_dashboard_overview(client, admin_token):
    r = client.get("/api/v1/admin/dashboards/overview",
                   headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    b = r.json()
    assert b["students_active"] >= 30  # mini-seed: 40 students, ~5 inactive
    assert 0.0 <= b["attendance_pct"] <= 100.0
    assert b["fees"]["billed_rs"] > 0
    assert "ml" in b


def test_dashboard_forbidden_for_student(client, student_token):
    r = client.get("/api/v1/admin/dashboards/overview",
                   headers=_auth(student_token["access_token"]))
    assert r.status_code == 403


def test_audit_log_records_logins(client, admin_token):
    r = client.get("/api/v1/admin/audit?limit=5",
                   headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected audit entries (logins are recorded)"
    assert all("content_hash" in x for x in rows)
