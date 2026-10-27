"""Students & admissions endpoints: list, detail, admissions, consent."""
from tests.conftest import _auth


def test_list_students_requires_admin_or_teacher(client, student_token):
    r = client.get("/api/v1/students", headers=_auth(student_token["access_token"]))
    assert r.status_code == 403


def test_list_students(client, admin_token):
    r = client.get("/api/v1/students?limit=5", headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert len(body["students"]) == 5
    s = body["students"][0]
    for key in ("id", "admission_no", "name", "outstanding_paise", "insights"):
        assert key in s


def test_student_detail(client, admin_token):
    lst = client.get("/api/v1/students?limit=1",
                     headers=_auth(admin_token["access_token"])).json()
    sid = lst["students"][0]["id"]
    r = client.get(f"/api/v1/students/{sid}",
                   headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == sid
    assert "exam_history" in body and "attendance_pct" in body


def test_student_detail_404(client, admin_token):
    r = client.get("/api/v1/students/999999",
                   headers=_auth(admin_token["access_token"]))
    assert r.status_code == 404


def test_student_portal_self_view(client, student_token):
    me = client.get("/api/v1/auth/me", headers=_auth(student_token["access_token"]))
    # the demo student (id 1) views their own record
    r = client.get("/api/v1/students/1",
                   headers=_auth(student_token["access_token"]))
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_guardian_portal_view_own_child_only(client, parent_token):
    # demo parent is linked to student 1
    ok = client.get("/api/v1/students/1",
                    headers=_auth(parent_token["access_token"]))
    assert ok.status_code == 200
    denied = client.get("/api/v1/students/2",
                        headers=_auth(parent_token["access_token"]))
    assert denied.status_code == 403


def test_admissions_endpoint_admin_only(client, teacher_token):
    r = client.get("/api/v1/students/1/admissions",
                   headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 403


def test_guardian_consent(client, admin_token):
    r = client.post("/api/v1/students/consent?student_id=1&grant=true",
                    headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    assert r.json()["consent_given"] is True
