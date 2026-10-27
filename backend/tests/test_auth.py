"""Auth: login / refresh / me + RBAC 401/403 paths."""
from tests.conftest import _auth, _login


def test_login_ok(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200
    body = r.json()
    assert body["role"] == "admin"
    assert body["access_token"] and body["refresh_token"]


def test_login_bad_credentials(client):
    r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_token(client):
    tok = _login(client)
    r = client.get("/api/v1/auth/me", headers=_auth(tok["access_token"]))
    assert r.status_code == 200
    assert r.json()["username"] == "admin"


def test_refresh_flow(client):
    tok = _login(client)
    r = client.post("/api/v1/auth/refresh",
                    json={"refresh_token": tok["refresh_token"]})
    assert r.status_code == 200
    new_access = r.json()["access_token"]
    r2 = client.get("/api/v1/auth/me", headers=_auth(new_access))
    assert r2.status_code == 200


def test_access_token_rejected_as_refresh(client):
    tok = _login(client)
    r = client.post("/api/v1/auth/refresh",
                    json={"refresh_token": tok["access_token"]})
    assert r.status_code == 401  # wrong token type


def test_rbac_admin_only_endpoint(client, teacher_token):
    r = client.get("/api/v1/fees/receipts/gap-audit?fiscal_year=2025",
                   headers=_auth(teacher_token["access_token"]))
    assert r.status_code == 403


def test_no_token_on_protected(client):
    assert client.get("/api/v1/students").status_code == 401
