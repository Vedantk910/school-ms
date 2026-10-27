"""Train GBDT + baselines with a temporal split, persist a ModelRegistry row.

Deterministic (sklearn seed fixed). Produces a reproducible metric report and
stores per-student SHAP explanations for the eval year.
"""
from __future__ import annotations

import json
import os

import joblib
import numpy as np
import shap
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)

from app.ml.features import FEATURES, build_dataset, split_temporal
from app.models import Insight, ModelRegistry

# Overridable so the container can mount a volume at /srv/artifacts
ARTIFACT_DIR = os.environ.get(
    "SCHOOLMS_ARTIFACT_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "artifacts"))


def _save_artifact(name: str, obj) -> str:
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    path = os.path.join(ARTIFACT_DIR, f"{name}.joblib")
    joblib.dump(obj, path)
    return path


def train_task(session, task: str) -> dict:
    """Train one task ('at_risk' | 'fee_default'), persist registry + insights."""
    df = build_dataset(session)
    train, ev = split_temporal(df)
    ycol = {"at_risk": "at_risk_label", "fee_default": "fee_default_label"}[task]
    label_name = ycol.replace("_label", "")

    Xtr, Xev = train[FEATURES], ev[FEATURES]
    ytr, yev = train[ycol].astype(int), ev[ycol].astype(int)

    model = HistGradientBoostingClassifier(
        max_iter=300, learning_rate=0.05, max_leaf_nodes=31, random_state=42)
    model.fit(Xtr, ytr)
    lr = LogisticRegression(max_iter=2000, random_state=42).fit(Xtr, ytr)

    p_gb, p_lr = model.predict_proba(Xev)[:, 1], lr.predict_proba(Xev)[:, 1]
    p_maj = np.full(len(yev), max(0.5, float(ytr.mean())))

    def metrics(p: np.ndarray, label: str) -> dict:
        yhat = (p >= 0.5).astype(int)
        return {
            "label": label,
            "auc": round(float(roc_auc_score(yev, p)), 4),
            "ap": round(float(average_precision_score(yev, p)), 4),
            "f1": round(float(f1_score(yev, yhat)), 4),
            "confusion": list(confusion_matrix(yev, yhat).ravel().tolist()),
            "n_eval": int(len(yev)), "base_rate": round(float(yev.mean()), 4),
        }

    rep = {
        "task": task,
        "split": {"train_years": ["2021-22", "2022-23", "2023-24", "2024-25"],
                   "eval_years": ["2025-26"]},
        "n_train": int(len(ytr)), "n_eval": int(len(yev)),
        "gbr": metrics(p_gb, "gbr"), "logreg": metrics(p_lr, "logreg"),
        "majority": metrics(p_maj, "majority"),
    }

    # Persist the model artifact + registry row
    artifact = _save_artifact(f"{task}_gbr_v1", model)
    reg = ModelRegistry(name=task, version=1, artifact_path=artifact,
                        metrics_json=json.dumps(rep),
                        train_years="2021-22..2024-25", eval_years="2025-26")
    session.add(reg)
    session.commit()
    session.refresh(reg)

    # SHAP explanations for the eval year (top-k per positive)
    from app.ml.explain import explain_gbr
    insights = explain_gbr(model, ev, task, session,
                           student_col="student_id", top_k=5)
    # purge stale insights for this task then insert fresh
    from sqlmodel import select
    from app.models import Insight as _I
    for i in session.exec(select(_I).where(_I.kind == task)).all():
        session.delete(i)
    session.flush()
    for ins in insights:
        session.add(ins)
    session.commit()

    rep["insights_stored"] = len(insights)
    return rep
