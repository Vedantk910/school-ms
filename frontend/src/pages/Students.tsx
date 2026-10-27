import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Students() {
  const { token } = useAuth();
  const [rows, setRows] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");

  useEffect(() => {
    api(`/students?q=${encodeURIComponent(q)}&limit=50`, { token }).then((d) => {
      setRows(d.students);
      setTotal(d.total);
    });
  }, [q, token]);

  return (
    <div>
      <h1>
        Students <span className="muted">({total})</span>
      </h1>
      <input
        className="search"
        placeholder="Search name or admission no…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <table className="table">
        <thead>
          <tr>
            <th>Adm No</th>
            <th>Name</th>
            <th>U-Id</th>
            <th>RTE/EWS</th>
            <th>Outstanding</th>
            <th>Open bills</th>
            <th>ML flags</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((s) => (
            <tr key={s.id}>
              <td>
                <Link to={`/students/${s.id}`}>{s.admission_no}</Link>
              </td>
              <td>{s.name}</td>
              <td>{s.uin}</td>
              <td>{s.rte_ews ? "yes" : "—"}</td>
              <td>₹{(s.outstanding_paise / 100).toLocaleString()}</td>
              <td>{s.open_bills}</td>
              <td>
                {s.insights.length
                  ? s.insights.map((i: any) => (
                      <span key={i.kind} className={`badge ${i.kind}`}>
                        {i.kind === "at_risk" ? "at-risk" : "fee"} {Math.round(i.score * 100)}%
                      </span>
                    ))
                  : <span className="muted">—</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
