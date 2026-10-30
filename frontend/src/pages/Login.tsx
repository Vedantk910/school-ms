import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import {
  IconBanknote,
  IconGradCap,
  IconShield,
  IconSparkles,
  IconUsers,
} from "../icons";

const DEMO: [string, string][] = [
  ["admin", "admin"],
  ["teach01", "teacher"],
  ["stud0001", "student"],
];

export default function Login() {
  const [u, setU] = useState("admin");
  const [p, setP] = useState("admin");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await login(u, p);
      nav("/");
    } catch (ex: any) {
      setErr(ex.message ?? "Sign-in failed. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-wrap">
      <aside className="login-panel" aria-hidden="true">
        <div className="login-brand">
          <span className="logo">
            <IconGradCap size={22} />
          </span>
          <div>
            <div className="brand-name">School-MS</div>
            <div className="brand-sub">MSBSHSE · 550 students</div>
          </div>
        </div>

        <div className="login-value">
          <h2>One calm system for a busy school.</h2>
          <p>
            Designed for a Maharashtra (MSBSHSE) school of 550 students — admissions, attendance,
            fee ledgers and board exam results in one place.
          </p>
          <div className="login-points">
            <div className="login-point">
              <span className="lp-icon"><IconUsers size={17} /></span>
              Live student records with RTE/EWS tracking
            </div>
            <div className="login-point">
              <span className="lp-icon"><IconBanknote size={17} /></span>
              Fee ledgers with numbered GST receipts
            </div>
            <div className="login-point">
              <span className="lp-icon"><IconSparkles size={17} /></span>
              Interpretable ML flags — at-risk &amp; fee-default
            </div>
          </div>
        </div>

        <div className="login-foot">
          <span className="login-point" style={{ fontSize: 12 }}>
            <span className="lp-icon" style={{ width: 22, height: 22, borderRadius: 6 }}>
              <IconShield size={13} />
            </span>
            Advisory only — verify against class records
          </span>
        </div>
      </aside>

      <main className="login-form-side">
        <form className="login-card" onSubmit={submit} noValidate>
          <div>
            <h1>Sign in</h1>
            <p className="login-sub">Enter your School-MS credentials for the 2025-26 session.</p>
          </div>

          <label>
            <span>Username</span>
            <input
              value={u}
              onChange={(e) => setU(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </label>
          <label>
            <span>Password</span>
            <input
              type="password"
              value={p}
              onChange={(e) => setP(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>

          {err && <div className="error" role="alert">{err}</div>}

          <button className="btn primary" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>

          <div className="demo-hint">
            <div className="demo-title">School accounts · password = role</div>
            <div className="chip-row">
              {DEMO.map(([a, b]) => (
                <button
                  key={a}
                  type="button"
                  className={`chip ${u === a ? "active" : ""}`}
                  onClick={() => {
                    setU(a);
                    setP(b);
                  }}
                >
                  {a}
                  <span className="muted" style={{ marginLeft: 6 }}>
                    {b}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </form>
      </main>
    </div>
  );
}
