import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  IconAward,
  IconRefresh,
  IconSparkles,
  IconTarget,
  IconTrendDown,
  IconTrendUp,
} from "../icons";
import { EmptyState, ErrorState, SkeletonCard, SkeletonStats } from "../ui";

type Kind = "at-risk" | "fee-default";

export default function Insights() {
  const { token } = useAuth();
  const [kind, setKind] = useState<Kind>("at-risk");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [models, setModels] = useState<any[]>([]);
  const [retraining, setRetraining] = useState(false);

  const load = useCallback(
    (k: Kind) => {
      setLoading(true);
      setFailed(false);
      api(`/ai/insights/${k}`, { token })
        .then(setData)
        .catch(() => setFailed(true))
        .finally(() => setLoading(false));
    },
    [token]
  );

  useEffect(() => {
    load(kind);
  }, [kind, load]);

  useEffect(() => {
    api("/ai/models", { token }).then(setModels).catch(() => {});
  }, [token]);

  function retrain() {
    setRetraining(true);
    api("/ai/train", { token, method: "POST" })
      .then(() => window.location.reload())
      .catch(() => setRetraining(false));
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: 16 }}>
        <div className="chip-row">
          <button
            className={`chip ${kind === "at-risk" ? "active" : ""}`}
            onClick={() => setKind("at-risk")}
            role="tab"
            aria-selected={kind === "at-risk"}
          >
            At-risk students
          </button>
          <button
            className={`chip ${kind === "fee-default" ? "active" : ""}`}
            onClick={() => setKind("fee-default")}
            role="tab"
            aria-selected={kind === "fee-default"}
          >
            Fee-default risk
          </button>
        </div>
        <button className="btn" onClick={retrain} disabled={retraining} style={{ marginLeft: "auto" }}>
          <IconRefresh size={15} style={{ transition: "transform .4s", transform: retraining ? "rotate(180deg)" : undefined }} />
          {retraining ? "Retraining…" : "Retrain models"}
        </button>
      </div>

      <div className="card">
        <p className="muted small" style={{ marginTop: 0 }}>
          Interpretable GBR model, temporal split (train 2021-24, eval 2025-26). Each flag shows
          the top-5 SHAP drivers. <b>Advisory output</b> — verify against class records before acting.
        </p>

        {loading ? (
          <SkeletonStats count={2} />
        ) : failed || !data ? (
          !loading && (
            <ErrorState
              title="No insights yet"
              body="The model has not been trained for this task, or the service is unavailable. Retrain to refresh."
              onRetry={() => load(kind)}
            />
          )
        ) : (
          <>
            <div className="stat-grid" style={{ marginBottom: 16 }}>
              <div className="stat">
                <div className={`stat-icon ${kind === "at-risk" ? "red" : "amber"}`}>
                  {kind === "at-risk" ? <IconTarget size={18} /> : <IconTrendDown size={18} />}
                </div>
                <div className="stat-label">Flagged students</div>
                <div className="stat-value">{data.count}</div>
                <div className="stat-sub">{kind === "at-risk" ? "academic risk this term" : "payment risk this term"}</div>
              </div>
              <div className="stat">
                <div className="stat-icon teal"><IconAward size={18} /></div>
                <div className="stat-label">Model</div>
                <div className="stat-value" style={{ fontSize: 18 }}>GBR v1</div>
                <div className="stat-sub">gradient-boosted, SHAP-explained</div>
              </div>
            </div>

            {data.insights.length === 0 ? (
              <EmptyState
                icon={<IconSparkles size={22} />}
                title="No students flagged"
                body="The model found no significant risk of this kind in the current cohort."
              />
            ) : (
              data.insights.map((i: any) => <InsightCard key={i.student_id} insight={i} />)
            )}
          </>
        )}
      </div>

      {models.length > 0 && (
        <div className="section">
          <h2>Model registry</h2>
          <div className="card" style={{ marginBottom: 0 }}>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Task</th>
                    <th className="num">Eval AUC</th>
                    <th className="num">Eval F1</th>
                    <th className="num">Base rate</th>
                    <th className="num">Insights stored</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.name}>
                      <td style={{ fontWeight: 550 }}>{m.name}</td>
                      <td className="num">{m.metrics.gbr.auc}</td>
                      <td className="num">{m.metrics.gbr.f1}</td>
                      <td className="num">{m.metrics.gbr.base_rate}</td>
                      <td className="num">{m.metrics.insights_stored ?? "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function InsightCard({ insight }: { insight: any }) {
  const kindCls = insight.kind === "at_risk" ? "at-risk" : "fee-default";
  return (
    <div className="card insight-card">
      <div className="insight-head">
        <span className={`stat-icon ${kindCls === "at-risk" ? "red" : "amber"}`} style={{ position: "static", width: 30, height: 30 }}>
          {kindCls === "at-risk" ? <IconTarget size={16} /> : <IconTrendDown size={16} />}
        </span>
        <b>Student #{insight.student_id}</b>
        <span className={`badge ${kindCls}`}>
          <span className="dot" />
          {kindCls === "at-risk" ? "at-risk" : "fee-default"} · {Math.round(insight.score * 100)}%
        </span>
        <span className="muted small" style={{ marginLeft: "auto" }}>{insight.model}</span>
      </div>
      <div className="muted small" style={{ margin: "10px 0 6px" }}>
        Why flagged — top SHAP drivers:
      </div>
      {insight.reasons?.length ? (
        <div className="shap-list">
          {insight.reasons.map((r: any, j: number) => (
            <div key={j} className="shap-item">
              <span className="shap-feature">{r.feature}</span>
              <div className="shap-bar">
                <div
                  className={`shap-fill ${r.direction}`}
                  style={{ width: `${Math.min(100, Math.abs(r.shap) * 200)}%` }}
                />
              </div>
              <span className="shap-value muted small">
                {r.value} · {r.shap}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="muted small">No explanation available for this flag.</div>
      )}
    </div>
  );
}
