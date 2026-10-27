import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Attendance() {
  const { token } = useAuth();
  const [s, setS] = useState<any>(null);
  const [d, setD] = useState("2025-04-07");
  const [written, setWritten] = useState<number | null>(null);

  useEffect(() => {
    api("/attendance/summary", { token }).then(setS).catch(() => {});
  }, [token, written]);

  return (
    <div>
      <h1>Attendance</h1>
      <div className="stat-grid">
        <div className="stat">
          <div className="stat-label">Present</div>
          <div className="stat-value">{s?.present ?? "—"}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Absent</div>
          <div className="stat-value">{s?.absent ?? "—"}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Leave</div>
          <div className="stat-value">{s?.leave ?? "—"}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Present %</div>
          <div className="stat-value">{s?.present_pct ?? "—"}%</div>
        </div>
      </div>

      <div className="card">
        <h2>Daily register entry</h2>
        <p className="muted small">
          Mark students 1-4 of section 6A for a sample date (demo write path).
        </p>
        <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 12 }}>
          <input type="date" value={d} onChange={(e) => setD(e.target.value)} />
          <button
            className="btn primary"
            onClick={() =>
              api("/attendance/register", {
                token,
                method: "POST",
                body: {
                  section: "6A",
                  d,
                  year_label: "2025-26",
                  entries: [[1, "P"], [2, "A"], [3, "P"], [4, "L"]],
                },
              })
                .then((r: any) => setWritten(r.written))
                .catch(() => setWritten(null))
            }
          >
            Save register
          </button>
          {written != null && <span className="muted">{written} entries written</span>}
        </div>
      </div>
    </div>
  );
}
