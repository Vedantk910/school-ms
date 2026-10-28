import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  IconBanknote,
  IconCalendar,
  IconRupee,
  IconSparkles,
  IconTarget,
  IconTrendDown,
  IconTrendUp,
  IconUserPlus,
  IconUsers,
} from "../icons";
import { ChartTooltip, ErrorState, SkeletonCard, SkeletonStats, formatLakhs } from "../ui";

const CHART_INK = "#66708a";
const GRID = "#edf0f6";

export default function Dashboard() {
  const { token } = useAuth();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api("/admin/dashboards/overview", { token })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(load, [load]);

  if (loading)
    return (
      <div>
        <SkeletonStats count={6} />
        <SkeletonCard lines={5} />
      </div>
    );

  if (!data)
    return (
      <ErrorState
        title="Dashboard unavailable"
        body="The overview is restricted to admin and teacher accounts. Check your role and try again."
        onRetry={load}
      />
    );

  const fees = data.fees;
  const feeData = [
    { name: "Billed", v: fees.billed_rs, color: "#3b50c4" },
    { name: "Collected", v: fees.collected_rs, color: "#0e8a7e" },
    { name: "Outstanding", v: fees.outstanding_rs, color: "#c93c3c" },
  ];
  const gap = fees.billed_rs - fees.collected_rs - fees.outstanding_rs;
  const trendUp = fees.collection_pct >= 80;

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <span className="badge advisory">
          <span className="dot" />
          Academic year 2025-26
        </span>
        <span className="muted small">All figures update with the live backend.</span>
      </div>

      <div className="stat-grid">
        <Stat
          icon={<IconUsers size={18} />}
          label="Active students"
          value={String(data.students_active)}
          sub="On the MSBSHSE register"
        />
        <Stat
          icon={<IconUserPlus size={18} />}
          tone="teal"
          label="Enrolments"
          value={String(data.enrollments)}
          sub="This academic year"
        />
        <Stat
          icon={<IconCalendar size={18} />}
          tone="teal"
          label="Attendance"
          value={`${data.attendance_pct}%`}
          sub="School-wide, today"
        />
        <Stat
          icon={<IconBanknote size={18} />}
          tone={trendUp ? "teal" : "red"}
          label="Fees collected"
          value={`${fees.collection_pct}%`}
          sub={`of ${formatLakhs(fees.billed_rs)} billed`}
          trend={
            trendUp
              ? <span className="stat-trend up"><IconTrendUp size={14} /> strong collection</span>
              : <span className="stat-trend down"><IconTrendDown size={14} /> behind target</span>
          }
        />
        <Stat
          icon={<IconTarget size={18} />}
          tone="red"
          label="At-risk flags (ML)"
          value={String(data.ml.at_risk_flags)}
          sub="Academic risk, GBR v1"
        />
        <Stat
          icon={<IconSparkles size={18} />}
          tone="amber"
          label="Fee-default flags (ML)"
          value={String(data.ml.fee_default_flags)}
          sub="Payment risk, GBR v1"
        />
      </div>

      <div className="section">
        <h2>Fees overview</h2>
        <div className="card">
          <div className="card-title">
            <h2 style={{ fontSize: 15 }}>Billed vs collected vs outstanding</h2>
            <span className="muted small">₹ · lakhs</span>
          </div>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={feeData} margin={{ top: 4, right: 8, left: 8, bottom: 0 }} barSize={64}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                <XAxis
                  dataKey="name"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: CHART_INK, fontSize: 12, fontWeight: 500 }}
                />
                <YAxis
                  tickLine={false}
                  axisLine={false}
                  width={56}
                  tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`}
                  tick={{ fill: CHART_INK, fontSize: 11 }}
                />
                <Tooltip
                  cursor={{ fill: "rgba(59,80,196,0.06)" }}
                  content={<ChartTooltip format={(v) => formatLakhs(v)} />}
                />
                <Bar dataKey="v" name="Amount" radius={[8, 8, 0, 0]} maxBarSize={64}>
                  {feeData.map((d) => (
                    <Cell key={d.name} fill={d.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-title">
            <h2 style={{ fontSize: 15 }}>Collection rate</h2>
            <span className={`badge ${trendUp ? "ok" : "warn"}`}>
              <span className="dot" />
              {fees.collection_pct}% collected
            </span>
          </div>
          <p style={{ marginTop: 0 }}>
            <b>{fees.collection_pct}%</b> of billed fees collected ({formatLakhs(fees.collected_rs)}).
            Outstanding: <b>{formatLakhs(fees.outstanding_rs)}</b>. The fee-default model flags
            students most likely to fall &gt;90 days behind — see{" "}
            <a href="#/insights">AI Insights</a>.
          </p>
          <div className="chart-box">
            <ResponsiveContainer width="100%" height={140}>
              <AreaChart
                data={[
                  { m: "Collected", v: fees.collected_rs },
                  { m: "Outstanding", v: fees.outstanding_rs },
                  { m: "Target gap", v: Math.max(0, gap) },
                ]}
                margin={{ top: 8, right: 8, left: 8, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="feeArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#0e8a7e" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="#0e8a7e" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                <XAxis
                  dataKey="m"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: CHART_INK, fontSize: 12, fontWeight: 500 }}
                />
                <YAxis
                  hide
                  tickFormatter={(v) => `₹${(v / 100000).toFixed(0)}L`}
                />
                <Tooltip
                  content={<ChartTooltip format={(v) => formatLakhs(v)} />}
                />
                <Area
                  type="monotone"
                  dataKey="v"
                  name="₹"
                  stroke="#0e8a7e"
                  strokeWidth={2.5}
                  fill="url(#feeArea)"
                  dot={{ r: 4, fill: "#0e8a7e", strokeWidth: 2, stroke: "#fff" }}
                  activeDot={{ r: 5 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="section">
        <h2>Advisory signals</h2>
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="row" style={{ marginBottom: 12 }}>
            <IconSparkles size={18} style={{ color: "var(--accent)" }} />
            <span className="small">
              {data.ml.at_risk_flags + data.ml.fee_default_flags} advisory flags this term —{" "}
              <a href="#/insights">review the explanations</a> before acting.
            </span>
          </div>
          <hr className="divider" style={{ margin: "14px 0" }} />
          <div className="row small muted">
            <IconRupee size={15} />
            <span>
              Fees outstanding of {formatLakhs(fees.outstanding_rs)} are tracked per-installment in{" "}
              <a href="#/fees">Fees &amp; Billing</a>.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({
  icon,
  tone = "",
  label,
  value,
  sub,
  trend,
}: {
  icon: React.ReactNode;
  tone?: string;
  label: string;
  value: string;
  sub?: string;
  trend?: React.ReactNode;
}) {
  return (
    <div className="stat">
      <div className={`stat-icon ${tone}`}>{icon}</div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {sub && <div className="stat-sub">{sub}</div>}
      {trend}
    </div>
  );
}
