"""SHAP-based explanations for the GBR models (the portfolio centerpiece).

Per predicted-positive student, we store the top-k (feature, value, shap)
tuples. SHAP on HistGBDT via TreeExplainer is fast enough on the capped
eval sample.
"""
from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd
import shap

from app.ml.features import FEATURES
from app.models import Insight


def explain_gbr(model, eval_df: pd.DataFrame, task: str, session,
                student_col: str = "student_id", top_k: int = 5,
                cap: int = 2000) -> list[Insight]:
    """Compute SHAP values for eval-year rows, return Insight rows for positives.

    ``cap`` bounds the SHAP call so the deterministic test run stays fast even
    at full scale; positives beyond the cap fall back to model-only scoring.
    """
    X = eval_df[FEATURES]
    s = shap.TreeExplainer(model)
    sample = X.head(cap)

    sv = s.shap_values(sample)
    if isinstance(sv, (list, tuple)):      # some versions return [class0, class1]
        sv = sv[1]
    sv = np.asarray(sv)
    base = np.asarray(s.expected_value)
    if base.ndim > 0:                       # per-class base values
        base = base[-1]
    shap_vals = (base + sv) if sv.ndim > 1 else np.zeros_like(X.iloc[0])

    p = model.predict_proba(X)[:, 1]
    labels = (p >= 0.5).astype(int)
    pos = np.where(labels == 1)[0]

    out: list[Insight] = []
    for row_i in pos:
        if row_i < cap:
            sv = np.ravel(shap_vals[row_i])
            order = np.argsort(-np.abs(sv))
            reasons: list[dict[str, Any]] = []
            for j in order[:top_k]:
                reasons.append({
                    "feature": str(FEATURES[j]),
                    "value": round(float(X.iloc[row_i, j]), 4),
                    "shap": round(float(sv[j]), 4),
                    "direction": "up" if sv[j] > 0 else "down",
                })
        else:
            reasons = []
        out.append(Insight(
            scope="student", student_id=int(eval_df.iloc[row_i][student_col]),
            kind=task, score=round(float(p[row_i]), 4), label=True,
            reasons_json=json.dumps(reasons), model_name=task, model_version=1))
    return out
