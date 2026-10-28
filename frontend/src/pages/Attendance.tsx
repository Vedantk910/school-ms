import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  IconCalendar,
  IconCheck,
  IconTrendDown,
  IconTrendUp,
} from "../icons";
import { ErrorState, SkeletonStats } from "../ui";

export default function Attendance() {
  const { token } = useAuth();
  const [s, setS] = useState<any>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [d, setD] = useState("2025-04-07");
  const [written, setWritten] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setFailed(false);
    api("/attendance/summary", { token })
      .then(setS)
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    load();
  }, [load, written]);

  async function save() {
    setSaving(true);
    try {
      const r: any = await api("/attendance/register", {
        token,
        method: "POST",
        body: {
          section: "6A",
          d,
          year_label: "2025-26",
          entries: [[1, "P"], [2, "A"], [3, "P"], [4, "L"]],
        },
      });
      setWritten(r.written);
    } catch {
      setWritten(null);
    } finally {
      setSaving(false);
    }
  }

  if (failed && !loading)
    return (
      <ErrorState
        title="Attendance summary unavailable"
        body="The daily register service is not responding."
        onRetry={load}
      />
    );

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <span className="badge advisory"><span className="dot" /> 6A register · AY 2025-26</span>
      </div>

      {loading ? (
        <SkeletonStats count={4} />
      ) : s ? (
        <div className="stat-grid">
          <div className="stat">
            <div className="stat-icon teal"><IconCheck size={18} /></div>
            <div className="stat-label">Present</div>
            <div className="stat-value">{s.present}</div>
            <div className="stat-sub">students in today's register</div>
          </div>
          <div className="stat">
            <div className="stat-icon red"><IconTrendDown size={18} /></div>
            <div className="stat-label">Absent</div>
            <div className="stat-value">{s.absent}</div>
            <div className="stat-sub">mark as P / A / L below</div>
          </div>
          <div className="stat">
            <div className="stat-icon amber"><IconCalendar size={18} /></div>
            <div className="stat-label">Leave</div>
            <div className="stat-value">{s.leave}</div>
            <div className="stat-sub">sanctioned, not counted absent</div>
          </div>
          <div className="stat">
            <div className="stat-icon"><IconTrendUp size={18} /></div>
            <div className="stat-label">Present %</div>
            <div className="stat-value">{s.present_pct}%</div>
            <div className="stat-sub">school-wide, today</div>
          </div>
        </div>
      ) : (
        !loading && (
          <ErrorState
            title="Attendance summary unavailable"
            body="The daily register service is not responding."
            onRetry={load}
          />
        )
      )}

      <div className="section">
        <h2>Daily register entry</h2>
        <div className="card" style={{ marginBottom: 0 }}>
          <p className="muted small" style={{ marginTop: 0 }}>
            Mark students 1-4 of section 6A for a sample date (demo write path). Entries are fixed
            to P, A, P, L for the demo.
          </p>
          <div className="inline-fields">
            <label className="field">
              <span>Register date</span>
              <input type="date" value={d} onChange={(e) => setD(e.target.value)} />
            </label>
            <button className="btn primary" onClick={save} disabled={saving}>
              {saving ? "Saving…" : "Save register"}
            </button>
          </div>
          {written != null && (
            <div className="badge ok" style={{ marginTop: 12 }}>
              <span className="dot" /> {written} entries written
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
