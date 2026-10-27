"""Test harness: fresh in-memory SQLite app + deterministic synthetic seed.

Two fixtures:
- ``client``: mini-seed (40 students, 15 school days) for fast API tests.
- ``ml_client``: full 550 students, 20 days/year for ML training tests
  (keeps attendance volume small while covering all 5 academic years).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("SCHOOLMS_DATABASE_URL", "sqlite:///:memory:")


def _seed(days_per_year: int, limit_students: int | None):
    from seeds.generate import build
    return build(days_per_year=days_per_year, limit_students=limit_students)


def _login(client, username="admin", password="admin") -> dict:
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client():
    from app.main import app
    _seed(days_per_year=15, limit_students=40)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def ml_client():
    from app.main import app
    _seed(days_per_year=20, limit_students=None)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def admin_token(client):
    return _login(client)


@pytest.fixture()
def teacher_token(client):
    return _login(client, "teach01", "teacher")


@pytest.fixture()
def parent_token(client):
    return _login(client, "parent01", "parent")


@pytest.fixture()
def student_token(client):
    return _login(client, "stud0001", "student")
