import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export default function StudentDetail({ id }: { id: string }) {
  const { token } = useAuth();
  const [s, setS] = useState<any>(null);

  useEffect(() => {
    api(`/students/${id}`, { token }).then(setS).catch(() => setS(null));
  }, [id, token]);

  if (!s) return <div className="muted">Not found</div>;

  return (
    <div>
      <h1>{s.name}</h1>
      <div className="muted">{s.admission_no} · {s.gender} · U-Id {s.uin} · DOB {s.dob}</div>

      <div className="stat-grid">
        <div className="stat">
          <div className="stat-label">Attendance (yr)</div>
          <div className="stat-value">{s.attendance_pct}%</div>
        </div>
        <div className="stat">
          <div className="stat-label">Outstanding</div>
          <div className="stat-value">₹{(s.outstanding_paise / 100).toLocaleString()}</div>
        </div>
      </div>

      <div className="card">
        <h2>Exam history</h2>
        {s.exam_history?.length ? (
          <table className="table">
            <thead>
              <tr>
                <th>Exam</th>
              </tr>
            </thead>
            <tbody>
              {s.exam_history.map((e: any, i: number) => (
                <tr key={i}>
                  <td>#{e.exam_id} — {e.pct}% · div {e.division} · {e.grade} ({e.pass}P/{e.fail}F)</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">No results published.</p>
        )}
      </div>

      <div className="card">
        <h2>AI insights</h2>
        {s.insights?.length ? (
          s.insights.map((i: any, k: number) => (
            <div key={k} className="insight-row">
              <span className={`badge ${i.kind}`}>
                {i.kind === "at_risk" ? "at-risk" : "fee-default"} {Math.round(i.score * 100)}%
              </span>
              <span className="muted small">{i.model}</span>
              {i.reasons?.length > 0 && (
                <div className="shap-list">
                  {i.reasons.map((r: any, j: number) => (
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
                  ))}
                </div>
              )}
            </div>
          ))
        ) : (
          <p className="muted">No flagged insights.</p>
        )}
      </div>
    </div>
  );
}
