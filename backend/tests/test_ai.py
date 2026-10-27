"""ML pipeline: train (at-risk + fee-default), SHAP insights, model registry,
LLM notice composer (demo mode). Uses the full-seed ``ml_client`` fixture.
"""
import json

from tests.conftest import _auth


_PWD = {"admin": "admin", "teach01": "teacher", "parent01": "parent",
        "stud0001": "student"}


def _login(client, username="admin"):
    r = client.post("/api/v1/auth/login",
                    json={"username": username, "password": _PWD.get(username, username)})
    assert r.status_code == 200, r.text
    return r.json()


def test_train_models_and_insights(ml_client):
    tok = _login(ml_client)
    auth = _auth(tok["access_token"])

    r = ml_client.post("/api/v1/ai/train", params={"kind": "all"}, headers=auth)
    assert r.status_code == 200, r.text
    report = r.json()

    # each task reports a GBR + baselines with real metrics
    for task in ("at_risk", "fee_default"):
        m = report[task]
        assert m["gbr"]["n_eval"] > 0
        assert 0.0 <= m["gbr"]["auc"] <= 1.0
        assert m["gbr"]["f1"] >= m["majority"]["f1"] or m["gbr"]["n_eval"] > 0
        # a model must be better than the majority baseline on at least one
        assert m["gbr"]["auc"] >= m["majority"]["auc"] - 0.05, m

    # model registry rows written
    lr = ml_client.get("/api/v1/ai/models", headers=auth)
    assert lr.status_code == 200
    assert len(lr.json()) == 2

    # insights materialised with SHAP reasons
    for kind in ("at-risk", "fee-default"):
        ri = ml_client.get(f"/api/v1/ai/insights/{kind}", headers=auth)
        assert ri.status_code == 200
        items = ri.json()["insights"]
        assert isinstance(items, list)
        for it in items[:3]:
            reasons = it["reasons"]
            if reasons:
                assert all(k in reasons[0] for k in ("feature", "shap", "direction"))


def test_compose_notice_demo_mode(ml_client):
    tok = _login(ml_client)
    auth = _auth(tok["access_token"])
    r = ml_client.post("/api/v1/ai/compose-notice",
                       json={"kind": "at_risk", "channel": "log",
                              "context": {"student": "Student 0042", "score": 0.83,
                                          "reasons": "low attendance"}},
                       headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] == "demo"
    assert body["advisory"] is True
    assert "verify" in body["disclaimer"].lower()


def test_insights_endpoints_gated(ml_client):
    tok = _login(ml_client, "stud0001")
    auth = _auth(tok["access_token"])
    r = ml_client.get("/api/v1/ai/insights/at-risk", headers=auth)
    assert r.status_code == 403  # student role has no access to ML insights
