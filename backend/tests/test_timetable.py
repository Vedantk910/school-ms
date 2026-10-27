"""Timetable: deterministic constraint solver + grid/solve endpoints + RBAC.

Solver constraints under test:
1. one teacher-class per (day, slot); 2. no >2 consecutive same-subject days;
3. first two subjects get a morning (slot<=4) slot; 4. exact period totals.
"""
from app.db import engine
from app.models import ClassSection
from app.timetable_solver import fill_week
from sqlmodel import Session, select
from tests.conftest import _auth

SUBJECTS = [
    {"subject_id": 1, "periods": 10, "teachers": [1, 2]},
    {"subject_id": 2, "periods": 8, "teachers": [3]},
    {"subject_id": 3, "periods": 6, "teachers": [4]},
    {"subject_id": 4, "periods": 4, "teachers": [5, 6]},
]  # 28 periods in 20 cells (4/day x 5) -> infeasible on purpose for one test


def test_determinism_same_seed_same_plan():
    a = fill_week(1, 4, [
        {"subject_id": 1, "periods": 10, "teachers": [1, 2]},
        {"subject_id": 2, "periods": 10, "teachers": [3]},
    ], seed=42)
    b = fill_week(1, 4, [
        {"subject_id": 1, "periods": 10, "teachers": [1, 2]},
        {"subject_id": 2, "periods": 10, "teachers": [3]},
    ], seed=42)
    assert a["solved"] and b["solved"]
    assert a["assignments"] == b["assignments"]


def test_different_seed_still_valid_but_may_differ():
    a = fill_week(2, 4, [
        {"subject_id": 1, "periods": 10, "teachers": [1, 2]},
        {"subject_id": 2, "periods": 10, "teachers": [3]},
    ], seed=42)
    b = fill_week(2, 4, [
        {"subject_id": 1, "periods": 10, "teachers": [1, 2]},
        {"subject_id": 2, "periods": 10, "teachers": [3]},
    ], seed=7)
    assert a["solved"] and b["solved"]
    for plan in (a, b):
        counts = {}
        for _d, _s, sid, _t in plan["assignments"]:
            counts[sid] = counts.get(sid, 0) + 1
        assert counts == {1: 10, 2: 10}  # constraint 4: exact totals


def test_constraints_honoured():
    plan = fill_week(3, 4, [
        {"subject_id": 1, "periods": 8, "teachers": [1]},
        {"subject_id": 2, "periods": 8, "teachers": [2]},
        {"subject_id": 3, "periods": 4, "teachers": [3]},
    ], seed=42)
    assert plan["solved"]
    # constraint 2: no 3-in-a-row of the same subject on any day
    by_day: dict[int, list[tuple[int, int]]] = {}
    for d, s, sid, _t in plan["assignments"]:
        by_day.setdefault(d, []).append((s, sid))
    for day, cells in by_day.items():
        cells.sort()
        run = 1
        for i in range(1, len(cells)):
            if cells[i][1] == cells[i - 1][1] and cells[i][0] == cells[i - 1][0] + 1:
                run += 1
            else:
                run = 1
            assert run <= 2, f"3-in-a-row violation day {day}"
    # constraint 1: a teacher is never in two classes at the same (day, slot)
    seen: set[tuple] = set()
    for d, s, sid, t in plan["assignments"]:
        if t is not None:
            key = (t, d, s)
            assert key not in seen, f"teacher {t} double-booked at day {d} slot {s}"
            seen.add(key)
    # constraint 3: first two subjects each occupy at least one morning slot
    used_morning_subj = {sid for _d, s, sid, _t in plan["assignments"] if s <= 4}
    assert 1 in used_morning_subj and 2 in used_morning_subj


def test_teacher_conflict_honoured():
    # teacher 1 is busy day1 slot1; subject 1 taught ONLY by teacher 1
    plan = fill_week(4, 4, [
        {"subject_id": 1, "periods": 4, "teachers": [1]},
    ], conflicts=[{"teacher_id": 1, "day": 1, "slot": 1}], seed=42)
    assert plan["solved"]
    assert not any(d == 1 and s == 1 and sid == 1 for d, s, sid, _t in plan["assignments"])


def test_infeasible_demand_returns_reason():
    plan = fill_week(5, 4, SUBJECTS, seed=42)
    assert not plan["solved"]
    assert plan["reason"] and "exceeds" in plan["reason"]


def test_solve_endpoint_and_grid(client, admin_token, teacher_token):
    # grab a real class_section id from the seed
    with Session(engine) as s:
        cs = s.exec(select(ClassSection)).first()
        csid = cs.id
    auth = _auth(admin_token["access_token"])
    body = {"class_section_id": csid, "slots_per_day": 4,
            "subjects": [
                {"subject_id": 1, "periods": 5, "teachers": [1]},
                {"subject_id": 2, "periods": 5, "teachers": [2]},
            ], "seed": 42}
    r = client.post("/api/v1/timetable/solve", json=body, headers=auth)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["solved"] is True and len(out["assignments"]) == 10
    # grid reflects the plan
    g = client.get(f"/api/v1/timetable/grid?class_section_id={csid}", headers=auth)
    assert g.status_code == 200
    total_cells = sum(len(d["cells"]) for d in g.json()["days"])
    assert total_cells == 10
    # student role is forbidden from solving
    denied = client.post("/api/v1/timetable/solve", json=body,
                         headers=_auth(student_role_token(client)))
    assert denied.status_code == 403
    # teacher may solve
    ok = client.post("/api/v1/timetable/solve", json=body,
                     headers=_auth(teacher_token["access_token"]))
    assert ok.status_code == 200


def student_role_token(client):
    from tests.conftest import _login
    return _login(client, "stud0001", "student")["access_token"]
