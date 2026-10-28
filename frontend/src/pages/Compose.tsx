import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  IconAlert,
  IconPen,
  IconSend,
  IconSparkles,
} from "../icons";

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
      <div className="row" style={{ marginBottom: 8 }}>
        <span className="badge advisory"><span className="dot" /> LLM notice drafts · advisory channel</span>
      </div>

      <div className="card">
        <div className="card-title">
          <h2 style={{ fontSize: 15 }}>Notice parameters</h2>
        </div>
        <div className="inline-fields">
          <label className="field">
            <span>Kind</span>
            <select value={kind} onChange={(e) => setKind(e.target.value as any)}>
              <option value="at_risk">At-risk support plan</option>
              <option value="fee_default">Fee default reminder</option>
              <option value="result_letter">Result letter</option>
            </select>
          </label>
          <label className="field">
            <span>Student</span>
            <input value={student} onChange={(e) => setStudent(e.target.value)} />
          </label>
          <button className="btn primary" onClick={compose} disabled={busy} style={{ alignSelf: "flex-end" }}>
            <IconPen size={16} />
            {busy ? "Composing…" : "Compose"}
          </button>
        </div>
        <hr className="divider" style={{ margin: "16px 0" }} />
        <p className="muted small" style={{ margin: 0 }}>
          Backend: <b>{result?.backend ?? "demo"}</b> — deterministic template engine by default;
          swap to Ollama/OpenRouter via <code>SCHOOLMS_LLM_BACKEND</code>. All output is flagged
          advisory.
        </p>
      </div>

      {result?.error && (
        <div className="error" role="alert">
          <IconAlert size={16} style={{ flex: "0 0 auto" }} />
          {result.error}
        </div>
      )}

      {result?.body && (
        <div className="card notice">
          <div className="card-title">
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <span className="stat-icon" style={{ position: "static", width: 30, height: 30 }}>
                <IconSend size={15} />
              </span>
              <b style={{ fontSize: 15 }}>{result.subject}</b>
              <span className="badge advisory">advisory · {result.backend}</span>
            </div>
          </div>
          <p style={{ margin: "0 0 12px", whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{result.body}</p>
          <div className="muted small" style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <IconAlert size={14} style={{ color: "var(--warn)", flex: "0 0 auto" }} />
            {result.disclaimer}
          </div>
        </div>
      )}

      {!result && (
        <div className="muted small" style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 4 }}>
          <IconSparkles size={14} />
          Composed notices appear here — pick a kind and press Compose.
        </div>
      )}
    </div>
  );
}
