// Shared page-state components: loading skeletons, empty & error screens
// with retry, and a small chart tooltip used by Recharts.
import { ReactNode } from "react";
import { IconAlert, IconSearch, IconX } from "./icons";

export function SkeletonCard({ lines = 4 }: { lines?: number }) {
  return (
    <div className="card" aria-busy="true" aria-label="Loading">
      <div className="skeleton skeleton-line w40" />
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={`skeleton skeleton-line ${i === lines - 1 ? "w70" : ""}`}
        />
      ))}
    </div>
  );
}

export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div className="stat-grid" aria-busy="true" aria-label="Loading">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="stat">
          <div className="skeleton skeleton-line w40" style={{ height: 12 }} />
          <div className="skeleton" style={{ height: 26, width: 90, marginTop: 4 }} />
        </div>
      ))}
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  body,
  action,
}: {
  icon?: ReactNode;
  title: string;
  body?: string;
  action?: ReactNode;
}) {
  return (
    <div className="state" role="status">
      <div className="state-icon">{icon ?? <IconSearch size={22} />}</div>
      <h3>{title}</h3>
      {body && <p>{body}</p>}
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  body,
  onRetry,
}: {
  title?: string;
  body?: string;
  onRetry?: () => void;
}) {
  return (
    <div className="state" role="alert">
      <div className="state-icon danger">
        <IconAlert size={22} />
      </div>
      <h3>{title}</h3>
      {body && <p>{body}</p>}
      {onRetry && (
        <button className="btn" onClick={onRetry}>
          <IconX size={16} />
          Try again
        </button>
      )}
    </div>
  );
}

// Soft, branded Recharts tooltip (used via the `content` prop)
export function ChartTooltip({
  active,
  payload,
  label,
  format,
}: {
  active?: boolean;
  payload?: { name?: string; value?: number | string; color?: string }[];
  label?: string;
  format?: (v: number) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div
      style={{
        background: "#16203a",
        color: "#fff",
        borderRadius: 10,
        padding: "10px 14px",
        boxShadow: "0 8px 24px -6px rgba(22,32,58,.4)",
        fontSize: 12.5,
        minWidth: 150,
      }}
    >
      {label != null && label !== "" && (
        <div style={{ color: "#9aa3b8", marginBottom: 6, fontWeight: 600 }}>{label}</div>
      )}
      {payload.map((p, i) => (
        <div
          key={i}
          style={{ display: "flex", alignItems: "center", gap: 8, marginTop: i ? 4 : 0 }}
        >
          <span
            style={{
              width: 9,
              height: 9,
              borderRadius: 3,
              background: p.color ?? "#3b50c4",
            }}
          />
          <span style={{ color: "#9aa3b8" }}>{p.name}</span>
          <span
            style={{
              marginLeft: "auto",
              fontWeight: 700,
              fontVariantNumeric: "tabular-nums",
            }}
          >
            {p.value == null ? "" : format ? format(Number(p.value)) : String(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function formatLakhs(rs: number): string {
  return `₹${(rs / 100000).toFixed(1)}L`;
}

export function formatINR(rs: number): string {
  return `₹${rs.toLocaleString("en-IN")}`;
}
