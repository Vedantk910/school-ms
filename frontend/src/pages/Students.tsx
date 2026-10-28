import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import { IconAlert, IconSearch, IconUsers, IconX } from "../icons";
import { EmptyState, ErrorState, SkeletonCard } from "../ui";

export default function Students() {
  const { token } = useAuth();
  const [rows, setRows] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setFailed(false);
    api(`/students?q=${encodeURIComponent(q)}&limit=50`, { token })
      .then((d) => {
        setRows(d.students ?? []);
        setTotal(d.total ?? 0);
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false));
  }, [q, token]);

  useEffect(load, [load]);

  return (
    <div>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: 16 }}>
        <div className="search">
          <IconSearch size={16} />
          <input
            placeholder="Search name, admission no or U-Id…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search students"
          />
        </div>
        <span className="muted small" aria-live="polite">
          {loading ? "Searching…" : `${total} student${total === 1 ? "" : "s"}`}
        </span>
      </div>

      {failed && !loading && (
        <ErrorState
          title="Could not load students"
          body="The student registry is not responding. Check your connection and try again."
          onRetry={load}
        />
      )}

      {loading ? (
        <SkeletonCard lines={8} />
      ) : !failed && rows.length === 0 ? (
        <EmptyState
          icon={<IconUsers size={22} />}
          title={q ? `No students match “${q}”` : "No students found"}
          body={q ? "Try a different name, admission number or U-Id." : "The register for this class is empty."}
          action={q ? <button className="btn" onClick={() => setQ("")}><IconX size={15} /> Clear search</button> : undefined}
        />
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th>Adm No</th>
                <th>Name</th>
                <th>U-Id</th>
                <th>RTE/EWS</th>
                <th className="num">Outstanding</th>
                <th className="num">Open bills</th>
                <th>ML flags</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => {
                const hasFlag = s.insights?.length > 0;
                return (
                  <tr key={s.id}>
                    <td>
                      <Link to={`/students/${s.id}`} aria-label={`Open ${s.name}`}>
                        {s.admission_no}
                      </Link>
                    </td>
                    <td style={{ fontWeight: 550, color: "var(--ink)" }}>{s.name}</td>
                    <td className="muted">{s.uin}</td>
                    <td>{s.rte_ews ? <span className="badge ok"><span className="dot" /> yes</span> : <span className="muted">—</span>}</td>
                    <td className="num">
                      {s.outstanding_paise > 0
                        ? <b style={{ color: s.outstanding_paise >= 1000000 ? "var(--danger)" : "var(--ink)" }}>₹{Math.round(s.outstanding_paise / 100).toLocaleString("en-IN")}</b>
                        : <span className="muted">₹0</span>}
                    </td>
                    <td className="num">{s.open_bills > 0 ? s.open_bills : <span className="muted">0</span>}</td>
                    <td>
                      {hasFlag ? (
                        s.insights.map((i: any) => (
                          <span key={i.kind} className={`badge ${i.kind === "at_risk" ? "at-risk" : "fee-default"}`} style={{ marginRight: 4 }}>
                            <span className="dot" />
                            {i.kind === "at_risk" ? "at-risk" : "fee"} {Math.round(i.score * 100)}%
                          </span>
                        ))
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {!loading && !failed && rows.length === 50 && (
        <div className="muted small" style={{ marginTop: 10, display: "flex", gap: 6, alignItems: "center" }}>
          <IconAlert size={14} /> Showing the first 50 of {total} — refine the search to narrow the list.
        </div>
      )}
    </div>
  );
}
