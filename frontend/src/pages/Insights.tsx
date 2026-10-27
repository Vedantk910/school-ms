import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

type Kind = "at-risk" | "fee-default";

export default function Insights() {
  const { token } = useAuth();
  const [kind, setKind] = useState<Kind>("at-risk");
  const [data, setData] = useState<any>(null);
  const [models, setModels] = useState<any[]>([]);

  useEffect(() => {
    api(`/ai/insights/${kind}`, { token }).then(setData).catch(() => setData(null));
  }, [kind, token]);

  useEffect(() => {
    api("/ai/models", { token }).then(setModels).catch(() => {});
  }, [token]);

  return (
    <div>
      <h1>AI Insights</h1>
      <div className="row" style={{ marginBottom: 16 }}>
        <button className={`chip ${kind === "at-risk" ? "active" : ""}`} onClick={() => setKind("at-risk")}>
          At-risk students
        </button>
        <button className={`chip ${kind === "fee-default" ? "active" : ""}`} onClick={() => setKind("fee-default")}>
          Fee-default risk
        </button>
        <button
          className="btn primary"
          onClick={() => api("/ai/train", { token, method: "POST" }).then(() => window.location.reload())}
        >
          Retrain models
        </button>
      </div>

      <div className="card">
        <p className="muted small">
          Interpretable GBR model, temporal split (train 2021-24, eval 2025-26).
          Each flag shows the SHAP top-5 drivers. Output is advisory — verify against class records.
        </p>
        {!data ? (
          <p className="muted">No insights yet. Train the models first.</p>
        ) : (
          <div className="stat-grid" style={{ marginBottom: 12 }}>
            <div className="stat">
              <div className="stat-label">Flagged students</div>
              <div className="stat-value">{data.count}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Model</div>
              <div className="stat-value small">GBR v1</div>
            </div>
          </div>
        )}

        {data && data.insights.length > 0 && (
          <div>
            {data.insights.map((i: any) => (
              <InsightCard key={i.student_id} insight={i} />
            ))}
          </div>
        )}
      </div>

      {models.length > 0 && (
        <div className="card">
          <h2>Model registry</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Task</th>
                <th>Eval AUC</th>
                <th>Eval F1</th>
                <th>Base rate</th>
                <th>Insights stored</th>
              </tr>
            </thead>
            <tbody>
              {models.map((m) => (
                <tr key={m.name}>
                  <td>{m.name}</td>
                  <td>{m.metrics.gbr.auc}</td>
                  <td>{m.metrics.gbr.f1}</td>
                  <td>{m.metrics.gbr.base_rate}</td>
                  <td>{m.metrics.insights_stored ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function InsightCard({ insight }: { insight: any }) {
  return (
    <div className="card insight-card">
      <div className="row">
        <b>Student #{insight.student_id}</b>
        <span className={`badge ${insight.kind === "at_risk" ? "at-risk" : "fee-default"}`}>
          {Math.round(insight.score * 100)}%
        </span>
        <span className="muted small">{insight.model}</span>
      </div>
      <div className="muted small" style={{ margin: "8px 0" }}>
        Why flagged (SHAP top-5):
      </div>
      {insight.reasons?.length ? (
        insight.reasons.map((r: any, j: number) => (
          <div key={j} className="shap-item">
            <span className="shap-feature">{r.feature}</span>
            <div className="shap-bar">
              <div
                className={`shap-fill ${r.direction}`}
                style={{ width: `${Math.min(100, Math.abs(r.shap) * 200)}%` }}
              />
            </div>
            <span className="muted small">
              {r.value} · {r.shap}
            </span>
          </div>
        ))
      ) : (
        <div className="muted small">no explanation available</div>
      )}
    </div>
  );
}
