import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Compose() {
  const { token } = useAuth();
  const [kind, setKind] = useState<"at_risk" | "fee_default" | "result_letter">("at_risk");
  const [student, setStudent] = useState("Student 0042");
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  async function compose() {
    setBusy(true);
    setResult(null);
    const ctx =
      kind === "result_letter"
        ? { student, exam: "HSC Board", pct: 88.5, division: 1, guardian: "Guardian" }
        : { student, score: 0.83, reasons: "low attendance, low internal marks",
            dues: "₹45,000", bills: 3 };
    try {
      setResult(
        await api("/ai/compose-notice", {
          token,
          method: "POST",
          body: { kind, audience: `student:${student}`, channel: "log", lang: "en", context: ctx },
        })
      );
    } catch (e: any) {
      setResult({ error: e.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1>Compose Notice (LLM adapter)</h1>
      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <label className="small">
            <span className="muted">Kind</span>
            <select value={kind} onChange={(e) => setKind(e.target.value as any)}>
              <option value="at_risk">At-risk support plan</option>
              <option value="fee_default">Fee default reminder</option>
              <option value="result_letter">Result letter</option>
            </select>
          </label>
          <label className="small">
            <span className="muted">Student</span>
            <input value={student} onChange={(e) => setStudent(e.target.value)} />
          </label>
          <button className="btn primary" onClick={compose} disabled={busy}>
            {busy ? "Composing…" : "Compose"}
          </button>
        </div>
        <p className="muted small">
          Backend: <b>{result?.backend ?? "demo"}</b> — deterministic template engine by default;
          swap to Ollama/OpenRouter via <code>SCHOOLMS_LLM_BACKEND</code>. All output is flagged
          advisory.
        </p>
      </div>

      {result?.error && <div className="error">{result.error}</div>}
      {result?.body && (
        <div className="card notice">
          <div className="row">
            <b>{result.subject}</b>
            <span className="badge advisory">advisory · {result.backend}</span>
          </div>
          <p style={{ margin: "12px 0" }}>{result.body}</p>
          <div className="muted small">⚠ {result.disclaimer}</div>
        </div>
      )}
    </div>
  );
}
