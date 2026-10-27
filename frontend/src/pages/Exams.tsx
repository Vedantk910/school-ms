import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Exams() {
  const { token } = useAuth();
  const [exams, setExams] = useState<any[]>([]);
  const [sel, setSel] = useState<number | null>(null);
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api("/exams?year_label=2025-26", { token }).then(setExams).catch(() => {});
  }, [token]);

  useEffect(() => {
    if (sel == null) return;
    api(`/exams/${sel}/results`, { token }).then(setRes).catch(() => setRes(null));
  }, [sel, token]);

  return (
    <div>
      <h1>Exams &amp; Results</h1>
      <div className="row">
        {exams.map((e) => (
          <button key={e.id} className={`chip ${sel === e.id ? "active" : ""}`} onClick={() => setSel(e.id)}>
            {e.name}
            <span className="muted"> · {e.weight_pct}%</span>
          </button>
        ))}
      </div>

      {res && (
        <div className="card">
          <h2>
            {res.name} — {res.examined} examined · avg {res.avg_pct}% · pass {res.pass_rate}%
          </h2>
          <div className="stat-grid">
            <div className="stat">
              <div className="stat-label">Average</div>
              <div className="stat-value">{res.avg_pct}%</div>
            </div>
            <div className="stat">
              <div className="stat-label">Pass rate</div>
              <div className="stat-value">{res.pass_rate}%</div>
            </div>
          </div>
          <h3>Top 10</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Student</th>
                <th>%</th>
                <th>Grade</th>
                <th>Division</th>
              </tr>
            </thead>
            <tbody>
              {res.top.map((t: any) => (
                <tr key={t.student_id}>
                  <td>{t.name}</td>
                  <td>{t.pct}%</td>
                  <td>{t.grade}</td>
                  <td>{t.division}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {err && <div className="error">{err}</div>}
    </div>
  );
}
