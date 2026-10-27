"""Staff HR + light payroll: create, leave lifecycle, payroll math, RBAC, audit.

Payroll model under test: net = base + allowances - (deductions + unpaid_days
x base//22), where unpaid_days = approved unpaid-leave days in the month."""
import json

from app.models.audit import AuditLog
from app.models.staff import StaffMember
from sqlmodel import Session, select
from app.db import engine
from tests.conftest import _auth


def _create_staff(admin_token, client, base_paise=4400000, allowances=0,
                  code="STF-100", name="Ms. Rao") -> int:
    r = client.post("/api/v1/staff", json={
        "staff_code": code, "name": name, "category": "teaching",
        "designation": "Senior Teacher", "joined_date": "2018-04-01",
        "monthly_base_paise": base_paise, "monthly_allowances_paise": allowances},
        headers=_auth(admin_token["access_token"]))
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_list_staff_requires_auth(client):
    assert client.get("/api/v1/staff").status_code == 401


def test_create_staff_and_payroll_math(client, admin_token, teacher_token):
    sid = _create_staff(admin_token, client, base_paise=4400000)  # 4.4L base
    auth = _auth(admin_token["access_token"])
    # 5 approved unpaid days in the month -> deduction = 5 * (4400000//22) = 1000000
    lv = client.post(f"/api/v1/staff/{sid}/leave",
                     json={"leave_type": "unpaid", "from_date": "2025-05-01",
                           "days": 5}, headers=auth)
    assert lv.status_code == 200 and lv.json()["days"] == 5
    lid = lv.json()["leave_id"]
    # teacher may not approve
    assert client.post(f"/api/v1/staff/leave/{lid}/approve",
                      headers=_auth(teacher_token["access_token"])).status_code == 403
    a = client.post(f"/api/v1/staff/leave/{lid}/approve", headers=auth)
    assert a.status_code == 200 and a.json()["status"] == "approved"

    r = client.post("/api/v1/staff/payroll/calculate",
                    json={"month": "2025-05"}, headers=auth)
    assert r.status_code == 200
    entry = next(e for e in r.json()["entries"] if e["staff_id"] == sid)
    # base 4400000 + 0 - (5 * 200000) = 3400000
    assert entry["unpaid_days"] == 5
    assert entry["net_paise"] == 4400000 - 5 * (4400000 // 22)
    assert entry["net_rs"] == "34000.00"


def test_rejected_leave_does_not_affect_payroll(client, admin_token):
    sid = _create_staff(admin_token, client, code="STF-200", base_paise=2200000)
    auth = _auth(admin_token["access_token"])
    lv = client.post(f"/api/v1/staff/{sid}/leave",
                     json={"leave_type": "unpaid", "from_date": "2025-06-02",
                           "days": 4}, headers=auth).json()
    rj = client.post(f"/api/v1/staff/leave/{lv['leave_id']}/reject", headers=auth)
    assert rj.json()["status"] == "rejected"
    r = client.post("/api/v1/staff/payroll/calculate", json={"month": "2025-06"},
                    headers=auth)
    entry = next(e for e in r.json()["entries"] if e["staff_id"] == sid)
    assert entry["unpaid_days"] == 0
    assert entry["net_paise"] == 2200000  # no deductions


def test_payroll_recalculate_is_idempotent(client, admin_token):
    sid = _create_staff(admin_token, client, code="STF-300", base_paise=3300000)
    auth = _auth(admin_token["access_token"])
    lv = client.post(f"/api/v1/staff/{sid}/leave",
                     json={"leave_type": "unpaid", "from_date": "2025-07-01",
                           "days": 3}, headers=auth)
    client.post(f"/api/v1/staff/leave/{lv.json()['leave_id']}/approve", headers=auth)
    for _ in range(2):
        r = client.post("/api/v1/staff/payroll/calculate", json={"month": "2025-07"},
                        headers=auth)
        assert r.status_code == 200
    # one entry per (staff, month) despite two calculations
    with Session(engine) as s:
        from app.models.staff import PayrollEntry
        rows = s.exec(select(PayrollEntry).where(
            PayrollEntry.staff_id == sid, PayrollEntry.month == "2025-07")).all()
        assert len(rows) == 1


def test_payroll_calc_admin_only(client, teacher_token):
    r = client.post("/api/v1/staff/payroll/calculate", json={"month": "2025-08"},
                    headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 403


def test_mutations_are_audit_logged(client, admin_token):
    sid = _create_staff(admin_token, client, code="STF-400")
    with Session(engine) as s:
        rows = s.exec(select(AuditLog).where(AuditLog.resource.like(f"staff%"))).all()
        assert any(f"staff#{sid}" in r.resource for r in rows)
