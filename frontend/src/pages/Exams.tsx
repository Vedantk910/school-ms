import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  IconAward,
  IconBook,
  IconCheck,
  IconTrendDown,
  IconTrendUp,
} from "../icons";
import { EmptyState, ErrorState, SkeletonCard, SkeletonStats } from "../ui";

export default function Exams() {
  const { token } = useAuth();
  const [exams, setExams] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [sel, setSel] = useState<number | null>(null);
  const [res, setRes] = useState<any>(null);
  const [resLoading, setResLoading] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setFailed(false);
    api("/exams?year_label=2025-26", { token })
      .then(setExams)
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (sel == null) return;
    setResLoading(true);
    api(`/exams/${sel}/results`, { token })
      .then((r) => {
        setRes(r);
        setResLoading(false);
      })
      .catch(() => {
        setRes(null);
        setResLoading(false);
      });
  }, [sel, token]);

  const strong = res ? res.pass_rate >= 80 : false;

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <span className="badge advisory"><span className="dot" /> Board & internal exams · 2025-26</span>
      </div>

      {failed && !loading ? (
        <ErrorState
          title="Exam list unavailable"
          body="The exam registry is not responding."
          onRetry={load}
        />
      ) : loading ? (
        <SkeletonStats count={2} />
      ) : (
        <>
          <div className="chip-row" role="tablist" aria-label="Exams" style={{ marginBottom: 16 }}>
            {exams.map((e, i) => (
              <button
                key={e.id}
                role="tab"
                aria-selected={sel === e.id}
                className={`chip ${sel === e.id ? "active" : ""}`}
                onClick={() => setSel(e.id)}
              >
                <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  {i === 0 && <IconBook size={14} />}
                  {e.name}
                  <span className="muted" style={{ opacity: sel === e.id ? 0.75 : undefined }}>
                    {e.weight_pct}%
                  </span>
                </span>
              </button>
            ))}
          </div>

          {resLoading ? (
            <SkeletonCard lines={6} />
          ) : res ? (
            <div className="card">
              <div className="card-title">
                <h2>{res.name}</h2>
                <span className="muted small">
                  {res.examined} examined · avg {res.avg_pct}% · pass {res.pass_rate}%
                </span>
              </div>
              <div className="stat-grid" style={{ marginBottom: 0 }}>
                <div className="stat">
                  <div className="stat-icon teal"><IconTrendUp size={18} /></div>
                  <div className="stat-label">Average</div>
                  <div className="stat-value">{res.avg_pct}%</div>
                  <div className="stat-sub">across all examined students</div>
                </div>
                <div className="stat">
                  <div className={`stat-icon ${strong ? "teal" : "red"}`}>
                    {strong ? <IconCheck size={18} /> : <IconTrendDown size={18} />}
                  </div>
                  <div className="stat-label">Pass rate</div>
                  <div className="stat-value">{res.pass_rate}%</div>
                  <div className="stat-sub">{strong ? "above 80% target" : "below 80% target"}</div>
                </div>
              </div>

              <h3>Top 10 scorers</h3>
              <div className="table-wrap" style={{ maxHeight: 320 }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th style={{ width: 56 }}>#</th>
                      <th>Student</th>
                      <th className="num">Score</th>
                      <th>Grade</th>
                      <th>Division</th>
                    </tr>
                  </thead>
                  <tbody>
                    {res.top.map((t: any, i: number) => (
                      <tr key={t.student_id}>
                        <td>
                          <span
                            className={`badge ${i < 3 ? "ok" : ""}`}
                            style={i < 3 ? { background: "var(--accent-soft)", color: "var(--accent-ink)" } : undefined}
                          >
                            {i + 1}
                          </span>
                        </td>
                        <td>
                          <span style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                            {i < 3 && <IconAward size={14} style={{ color: "var(--accent)" }} />}
                            {t.name}
                          </span>
                        </td>
                        <td className="num"><b>{t.pct}%</b></td>
                        <td><span className="badge">{t.grade}</span></td>
                        <td>{t.division}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            !resLoading && (
              <EmptyState
                icon={<IconBook size={22} />}
                title="No results selected"
                body="Pick an exam above to see the top scorers and pass-rate summary."
              />
            )
          )}
        </>
      )}
    </div>
  );
}
