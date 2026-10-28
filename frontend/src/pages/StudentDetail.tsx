import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  IconAward,
  IconBanknote,
  IconCalendar,
  IconSparkles,
  IconUser,
} from "../icons";
import { EmptyState, ErrorState, SkeletonCard } from "../ui";

export default function StudentDetail({ id }: { id: string }) {
  const { token } = useAuth();
  const [s, setS] = useState<any>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    setFailed(false);
    api(`/students/${id}`, { token })
      .then(setS)
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [id, token]);

  useEffect(load, [load]);

  if (loading) return <SkeletonCard lines={6} />;

  if (failed || !s)
    return (
      <ErrorState
        title="Student not found"
        body={`No record exists for student #${id}. It may have been archived.`}
        onRetry={load}
      />
    );

  const outstandingRs = Math.round(s.outstanding_paise / 100);

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Link to="/students" className="muted small" style={{ display: "inline-flex", gap: 5, marginBottom: 6 }}>
          <IconUser size={14} /> Back to students
        </Link>
        <div className="row" style={{ gap: 14, alignItems: "flex-start" }}>
          <span className="avatar" style={{ width: 46, height: 46, fontSize: 16 }} aria-hidden="true">
            {s.name
              .split(" ")
              .filter(Boolean)
              .slice(0, 2)
              .map((w: string) => w[0].toUpperCase())
              .join("")}
          </span>
          <div>
            <h1>{s.name}</h1>
            <div className="muted small" style={{ marginTop: 2 }}>
              {s.admission_no} · {s.gender} · U-Id {s.uin} · DOB {s.dob}
            </div>
          </div>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat">
          <div className="stat-icon teal"><IconCalendar size={18} /></div>
          <div className="stat-label">Attendance (yr)</div>
          <div className="stat-value">{s.attendance_pct}%</div>
          <div className="stat-sub">of required days present</div>
        </div>
        <div className="stat">
          <div className={`stat-icon ${outstandingRs > 0 ? "red" : "teal"}`}>
            <IconBanknote size={18} />
          </div>
          <div className="stat-label">Outstanding</div>
          <div className="stat-value">₹{outstandingRs.toLocaleString("en-IN")}</div>
          <div className="stat-sub">
            {outstandingRs > 0 ? "across open bills" : "all bills cleared"}
          </div>
        </div>
      </div>

      <div className="section">
        <h2>Exam history</h2>
        <div className="card" style={{ marginBottom: 0 }}>
          {s.exam_history?.length ? (
            <div className="table-wrap" style={{ maxHeight: 300 }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Exam</th>
                    <th className="num">Score</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {s.exam_history.map((e: any, i: number) => (
                    <tr key={i}>
                      <td>#{e.exam_id}</td>
                      <td className="num">
                        <b>{e.pct}%</b> · div {e.division}
                      </td>
                      <td>
                        <span className={`badge ${e.pass > 0 ? "ok" : "at-risk"}`}>
                          <span className="dot" /> {e.grade} · {e.pass}P/{e.fail}F
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState
              icon={<IconAward size={22} />}
              title="No results published"
              body="Board and internal exam results will appear here once published."
            />
          )}
        </div>
      </div>

      <div className="section">
        <h2>AI insights</h2>
        <div className="card" style={{ marginBottom: 0 }}>
          {s.insights?.length ? (
            s.insights.map((i: any, k: number) => (
              <div key={k} className="insight-card card" style={{ marginBottom: k < s.insights.length - 1 ? 12 : 0 }}>
                <div className="insight-head">
                  <IconSparkles size={17} style={{ color: "var(--accent)" }} />
                  <b>#{i.student_id}</b>
                  <span className={`badge ${i.kind === "at_risk" ? "at-risk" : "fee-default"}`}>
                    <span className="dot" />
                    {i.kind === "at_risk" ? "at-risk" : "fee-default"} {Math.round(i.score * 100)}%
                  </span>
                  <span className="muted small" style={{ marginLeft: "auto" }}>{i.model}</span>
                </div>
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
                        <span className="shap-value muted small">{r.value} · {r.shap}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          ) : (
            <EmptyState
              icon={<IconSparkles size={22} />}
              title="No flagged insights"
              body="The ML models are not flagging this student this term."
            />
          )}
        </div>
      </div>
    </div>
  );
}
