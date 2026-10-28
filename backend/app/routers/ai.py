"""AI service: ML training, at-risk / fee-default insights (SHAP-explained),
LLM notice composition (demo-mode default). All outputs advisory."""
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlmodel import Session, select

from app.audit import record
from app.db import get_session
from app.dependencies import require_roles
from app.llm import get_llm
from app.models import Insight, ModelRegistry, OutboxMessage, User

router = APIRouter(prefix="/ai", tags=["ai"])


class ComposeIn(BaseModel):
    kind: Literal["at_risk", "fee_default", "result_letter"] = "result_letter"
    context: dict = {}
    audience: str = "all"
    lang: str = "en"
    channel: str = "inapp"  # inapp | log (demo keeps cost at zero)


@router.get("/insights/at-risk")
def at_risk_insights(
    limit: int = Query(default=20, le=200),
    session: Session = Depends(get_session),
    user: User = Depends(require_roles("admin", "teacher")),
):
    rows = session.exec(select(Insight).where(Insight.kind == "at_risk", Insight.label == True)  # noqa: E712
                         .order_by(Insight.score.desc())).all()
    return {"count": len(rows), "insights": [
        {"student_id": i.student_id, "score": round(i.score, 4),
         "model": f"{i.model_name} v{i.model_version}",
         "reasons": json.loads(i.reasons_json or "[]"),
         "created_at": str(i.created_at)}
        for i in rows[:limit]
    ]}


@router.get("/insights/fee-default")
def fee_default_insights(
    limit: int = Query(default=20, le=200),
    session: Session = Depends(get_session),
    user: User = Depends(require_roles("admin", "teacher")),
):
    rows = session.exec(select(Insight).where(Insight.kind == "fee_default", Insight.label == True)  # noqa: E712
                         .order_by(Insight.score.desc())).all()
    return {"count": len(rows), "insights": [
        {"student_id": i.student_id, "score": round(i.score, 4),
         "model": f"{i.model_name} v{i.model_version}",
         "reasons": json.loads(i.reasons_json or "[]"),
         "created_at": str(i.created_at)}
        for i in rows[:limit]
    ]}


@router.get("/models")
def list_models(session: Session = Depends(get_session),
                user: User = Depends(require_roles("admin"))):
    rows = session.exec(select(ModelRegistry)).all()
    return [{"name": m.name, "version": m.version,
             "metrics": json.loads(m.metrics_json or "{}"),
             "train_years": m.train_years, "eval_years": m.eval_years,
             "trained_at": str(m.trained_at)} for m in rows]


@router.post("/train")
def train_models(
    kind: Literal["at_risk", "fee_default", "all"] = Query(default="all"),
    session: Session = Depends(get_session),
    user: User = Depends(require_roles("admin")),
):
    try:
        from app.ml.train import train_task
    except ModuleNotFoundError as exc:  # no ML stack bundled (serverless runtime)
        raise HTTPException(
            status_code=501,
            detail=(
                "Model training is not available in this runtime (ML stack not "
                "bundled on the serverless host). The insights endpoints read "
                f"pre-materialised results; train via `tools/bootstrap_db.py "
                f"--retrain` against the database. Missing: {exc.name}"
            ),
        )
    results = {}
    for task in (["at_risk", "fee_default"] if kind == "all" else [kind]):
        results[task] = train_task(session, task)
    return results


@router.post("/compose-notice")
def compose_notice(body: ComposeIn, session: Session = Depends(get_session),
                   user: User = Depends(require_roles("admin", "teacher"))):
    llm = get_llm()
    res = llm.compose_notice(context={**body.context, "kind": body.kind}, lang=body.lang)
    msg = OutboxMessage(template=body.kind, audience=body.audience, channel=body.channel,
                        lang=body.lang, subject=res.subject, body=res.body, advisory=res.advisory)
    if body.channel == "log":
        msg.sent_state = "sent"  # log-mode: pretend delivered, no real gateway
    session.add(msg)
    session.commit()
    record(session, actor=user.username, action="create",
           resource=f"outbox#{msg.id}", detail={"kind": body.kind, "backend": res.backend,
                                                "advisory": res.advisory})
    return {"outbox_id": msg.id, "subject": res.subject, "body": res.body,
            "advisory": res.advisory, "backend": res.backend,
            "disclaimer": "Advisory output; verify against official records before sending."}
