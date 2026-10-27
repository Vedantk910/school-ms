"""Exams & gradebook: list, results, mark entry + result recomputation."""
from tests.conftest import _auth


def test_list_exams(client, admin_token):
    r = client.get("/api/v1/exams?year_label=2025-26",
                   headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    names = [e["name"] for e in r.json()]
    assert "HSC Board" in names and "Internal 1" in names


def test_exam_results(client, admin_token):
    exams = client.get("/api/v1/exams?year_label=2025-26",
                       headers=_auth(admin_token["access_token"])).json()
    board = next(e for e in exams if e["name"] == "HSC Board")
    r = client.get(f"/api/v1/exams/{board['id']}/results",
                   headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["examined"] >= 1
    assert 0.0 <= body["avg_pct"] <= 100.0
    assert body["top"], "expected a top-10 list"


def test_enter_marks_recomputes_results(client, teacher_token):
    exams = client.get("/api/v1/exams?year_label=2025-26",
                       headers=_auth(teacher_token["access_token"])).json()
    internal = next(e for e in exams if e["name"] == "Internal 1")
    r = client.post(f"/api/v1/exams/{internal['id']}/marks",
                    json={"exam_id": internal["id"],
                          "marks": [{"student_id": 1, "theory": 60,
                                     "practical": 20, "subject_code": "EN"}]},
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 200
    assert r.json()["marks_written"] == 1


def test_enter_marks_rejects_overscore(client, teacher_token):
    exams = client.get("/api/v1/exams?year_label=2025-26",
                       headers=_auth(teacher_token["access_token"])).json()
    internal = next(e for e in exams if e["name"] == "Internal 1")
    r = client.post(f"/api/v1/exams/{internal['id']}/marks",
                    json={"exam_id": internal["id"],
                          "marks": [{"student_id": 1, "theory": 999,
                                     "subject_code": "EN"}]},
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 400


def test_publish_results_admin_only(client, teacher_token):
    exams = client.get("/api/v1/exams?year_label=2025-26",
                       headers=_auth(teacher_token["access_token"])).json()
    r = client.post(f"/api/v1/exams/{exams[0]['id']}/publish",
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 403


def test_publish_results(client, admin_token):
    exams = client.get("/api/v1/exams?year_label=2025-26",
                       headers=_auth(admin_token["access_token"])).json()
    r = client.post(f"/api/v1/exams/{exams[0]['id']}/publish",
                    headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200
    assert r.json()["published_rows"] >= 1
