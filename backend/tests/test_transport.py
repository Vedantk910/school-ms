"""Transport: stop ordering, assignment + revenue math, role gating.

Routes/stops are created via a direct ORM session (the API has no route
create endpoint - admin builds routes in the DB); the API endpoints are
then exercised through the TestClient, reusing conftest fixtures.
"""
from sqlmodel import Session, select

from app.db import engine
from app.models import AcademicYear
from app.models.transport import Route, RouteStop, TransportAssignment
from tests.conftest import _auth


def _make_route(name: str, stops: list[tuple[str, int]]) -> int:
    with Session(engine) as s:
        year = s.exec(select(AcademicYear).where(AcademicYear.label == "2025-26")).one()
        r = Route(year_id=year.id, name=name, level=10, direction="outbound")
        s.add(r)
        s.commit()
        s.refresh(r)
        for seq, (stop_name, charge) in enumerate(stops, start=1):
            s.add(RouteStop(route_id=r.id, sequence=seq, stop_name=stop_name,
                           charge_paise=charge))
        s.commit()
        return r.id


def test_route_detail_stop_ordering_and_charges(client, admin_token):
    rid = _make_route("East Run", [("East Gate", 50000), ("Main Road", 40000), ("Market", 30000)])
    auth = _auth(admin_token["access_token"])
    lst = client.get("/api/v1/transport/routes?year_label=2025-26", headers=auth)
    assert lst.status_code == 200
    assert any(x["id"] == rid for x in lst.json())
    detail = client.get(f"/api/v1/transport/routes/{rid}", headers=auth)
    assert detail.status_code == 200
    stops = detail.json()["stops"]
    assert [x["stop_name"] for x in stops] == ["East Gate", "Main Road", "Market"]
    assert [x["sequence"] for x in stops] == [1, 2, 3]
    assert stops[0]["charge_paise"] == 50000 and stops[0]["charge_rs"] == "500.00"


def test_assign_creates_row_and_revenue_math(client, admin_token):
    rid = _make_route("West Run", [("Stop A", 60000), ("Stop B", 40000)])
    auth = _auth(admin_token["access_token"])
    r1 = client.post(f"/api/v1/transport/routes/{rid}/assign",
                     json={"student_id": 1, "stop_name": "Stop A"}, headers=auth)
    assert r1.status_code == 200
    assert r1.json()["monthly_charge_paise"] == 60000
    r2 = client.post(f"/api/v1/transport/routes/{rid}/assign",
                     json={"student_id": 2, "stop_name": "Stop A"}, headers=auth)
    assert r2.status_code == 200
    got = client.get("/api/v1/transport/assignments?stop=Stop A", headers=auth)
    assert got.status_code == 200
    by_stop = got.json()["revenue_by_stop"]
    row = next(x for x in by_stop if x["stop_name"] == "Stop A")
    # two active students at Stop A, each at the stop's default charge 60000
    assert row["monthly_paise"] == 120000 and row["monthly_rs"] == "1200.00"


def test_assignments_filtered_by_stop(client, admin_token):
    rid = _make_route("Night Run", [("North", 20000), ("South", 25000)])
    auth = _auth(admin_token["access_token"])
    client.post(f"/api/v1/transport/routes/{rid}/assign",
                json={"student_id": 1, "stop_name": "North"}, headers=auth)
    # unfiltered view: only North is assigned, so only North has revenue
    all_stops = client.get("/api/v1/transport/assignments", headers=auth).json()
    assert [x["stop_name"] for x in all_stops["revenue_by_stop"]] == ["North"]
    assert all_stops["revenue_by_stop"][0]["monthly_paise"] == 20000
    # filter to South -> no assignments there -> empty revenue_by_stop
    got = client.get("/api/v1/transport/assignments?stop=South", headers=auth)
    assert got.status_code == 200
    assert got.json()["active_assignments"] == 0
    assert got.json()["revenue_by_stop"] == []


def test_teacher_reads_parent_cannot_assign(client, teacher_token, parent_token):
    rid = _make_route("Staff Run", [("Gate", 10000)])
    assert client.get(f"/api/v1/transport/routes/{rid}",
                      headers=_auth(teacher_token["access_token"])).status_code == 200
    r = client.post(f"/api/v1/transport/routes/{rid}/assign",
                    json={"student_id": 1, "stop_name": "Gate"},
                    headers=_auth(parent_token["access_token"]))
    assert r.status_code == 403
