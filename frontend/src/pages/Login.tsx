import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

const DEMO: [string, string][] = [
  ["admin", "admin"],
  ["teach01", "teacher"],
  ["parent01", "parent"],
  ["stud0001", "student"],
];

export default function Login() {
  const [u, setU] = useState("admin");
  const [p, setP] = useState("admin");
  const [err, setErr] = useState("");
  const { login } = useAuth();
  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await login(u, p);
      nav("/");
    } catch (ex: any) {
      setErr(ex.message ?? "login failed");
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand">
          <span className="logo">MS</span>
          <div>
            <div className="brand-name">School-MS</div>
            <div className="brand-sub">End-to-end school management · MSBSHSE</div>
          </div>
        </div>
        <label>
          <span>Username</span>
          <input value={u} onChange={(e) => setU(e.target.value)} autoComplete="username" />
        </label>
        <label>
          <span>Password</span>
          <input type="password" value={p} onChange={(e) => setP(e.target.value)} />
        </label>
        {err && <div className="error">{err}</div>}
        <button className="btn primary" type="submit">
          Sign in
        </button>
        <div className="demo-hint">
          <div className="muted small">Demo accounts (username / password):</div>
          {DEMO.map(([a, b]) => (
            <button
              key={a}
              type="button"
              className="chip"
              onClick={() => {
                setU(a);
                setP(b);
              }}
            >
              {a} / {b}
            </button>
          ))}
        </div>
      </form>
    </div>
  );
}
