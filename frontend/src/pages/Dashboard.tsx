import { useEffect, useState } from "react";
import {
  Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Dashboard() {
  const { token } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api("/admin/dashboards/overview", { token })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) return <div className="muted">Loading dashboard…</div>;
  if (!data) return <div className="error">Dashboard unavailable (admin/teacher only).</div>;

  const fees = data.fees;
  const feeData = [
    { name: "Billed", v: fees.billed_rs },
    { name: "Collected", v: fees.collected_rs },
    { name: "Outstanding", v: fees.outstanding_rs },
  ];

  return (
    <div>
      <h1>Academic Year 2025-26</h1>
      <div className="stat-grid">
        <Stat label="Active students" value={String(data.students_active)} />
        <Stat label="Enrolments" value={String(data.enrollments)} />
        <Stat label="Attendance" value={`${data.attendance_pct}%`} />
        <Stat
          label="Fees collected"
          value={`${fees.collection_pct}%`}
          sub={`₹${(fees.collected_rs / 100000).toFixed(1)}L of ₹${(fees.billed_rs / 100000).toFixed(1)}L`}
        />
        <Stat label="At-risk flags (ML)" value={String(data.ml.at_risk_flags)} />
        <Stat label="Fee-default flags (ML)" value={String(data.ml.fee_default_flags)} />
      </div>

      <div className="card">
        <h2>Fees: billed vs collected vs outstanding (₹)</h2>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={feeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`} />
            <Tooltip formatter={(v: number) => `₹${(v / 100000).toFixed(1)} lakh`} />
            <Bar dataKey="v" fill="#4f8ef7" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card">
        <h2>Collection rate</h2>
        <p>
          <b>{fees.collection_pct}%</b> of billed fees collected. Outstanding:{" "}
          <b>₹{fees.outstanding_rs.toLocaleString()}</b>. The fee-default model flags
          students most likely to fall &gt;90 days behind — see{" "}
          <a href="#/insights">AI Insights</a>.
        </p>
        <ResponsiveContainer width="100%" height={120}>
          <LineChart
            data={[
              { m: "Collected", v: fees.collected_rs },
              { m: "Outstanding", v: fees.outstanding_rs },
            ]}
          >
            <XAxis dataKey="m" />
            <Tooltip formatter={(v: number) => `₹${(v / 100000).toFixed(1)}L`} />
            <Line type="monotone" dataKey="v" stroke="#e05c5c" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="muted small">{sub}</div>}
    </div>
  );
}
