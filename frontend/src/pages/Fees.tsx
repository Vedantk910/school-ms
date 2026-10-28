import { useCallback, useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  IconBanknote,
  IconCheck,
  IconRupee,
  IconSearch,
} from "../icons";
import { EmptyState, ErrorState, SkeletonCard } from "../ui";

function ledgerTone(b: any): string {
  if (b.waived) return "ok";
  if (b.status === "paid" || b.status === "PAID") return "ok";
  if (b.status === "due" || b.status === "DUE" || b.status === "overdue") return "warn";
  return "";
}

export default function Fees() {
  const { token } = useAuth();
  const [sid, setSid] = useState("1");
  const [ledger, setLedger] = useState<any>(null);
  const [ledErr, setLedErr] = useState(false);
  const [ledLoading, setLedLoading] = useState(true);
  const [receiptNo, setReceiptNo] = useState("");
  const [receipt, setReceipt] = useState<any>(null);
  const [receiptLoading, setReceiptLoading] = useState(false);
  const [amount, setAmount] = useState(100000);
  const [last, setLast] = useState<any>(null);
  const [paying, setPaying] = useState(false);

  const loadLedger = useCallback((id: string) => {
    setLedLoading(true);
    setLedErr(false);
    setLedger(null);
    api(`/fees/student-ledger/${id}`, { token })
      .then(setLedger)
      .catch(() => setLedErr(true))
      .finally(() => setLedLoading(false));
  }, [token]);

  useEffect(() => {
    loadLedger(sid);
  }, [sid, loadLedger]);

  async function recordPayment() {
    setPaying(true);
    try {
      setLast(
        await api("/fees/payments", {
          token,
          method: "POST",
          body: { student_id: Number(sid), amount_paise: amount, mode: "upi" },
        })
      );
      loadLedger(sid); // reflect the new ledger state
    } catch {
      setLast(null);
    } finally {
      setPaying(false);
    }
  }

  async function loadReceipt() {
    setReceiptLoading(true);
    api(`/fees/receipt/${encodeURIComponent(receiptNo)}`, { token })
      .then(setReceipt)
      .catch(() => setReceipt(null))
      .finally(() => setReceiptLoading(false));
  }

  return (
    <div>
      <div className="row" style={{ marginBottom: 8 }}>
        <span className="badge advisory"><span className="dot" /> Installments, payments & GST receipts</span>
      </div>

      {/* ledger */}
      <div className="card">
        <div className="card-title">
          <h2 style={{ fontSize: 15 }}>Student ledger</h2>
        </div>
        <div className="inline-fields" style={{ marginBottom: 14 }}>
          <label className="field" style={{ minWidth: 160 }}>
            <span>Student ID</span>
            <input value={sid} onChange={(e) => setSid(e.target.value)} aria-label="Student ID" />
          </label>
        </div>

        {ledLoading ? (
          <SkeletonCard lines={4} />
        ) : ledErr ? (
          <ErrorState
            title="Ledger unavailable"
            body={`No ledger found for student ${sid}. Check the ID and retry.`}
            onRetry={() => loadLedger(sid)}
          />
        ) : ledger ? (
          <>
            <div className="table-wrap" style={{ maxHeight: 320 }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Installment</th>
                    <th>Due</th>
                    <th>Status</th>
                    <th className="num">Total</th>
                    <th className="num">Paid</th>
                  </tr>
                </thead>
                <tbody>
                  {ledger.bills.map((b: any) => (
                    <tr key={b.installment}>
                      <td style={{ fontWeight: 550 }}>{b.installment}</td>
                      <td>{b.due}</td>
                      <td>
                        {b.waived ? (
                          <span className="badge waived"><span className="dot" /> waived</span>
                        ) : (
                          <span className={`badge ${ledgerTone(b)}`}><span className="dot" /> {b.status}</span>
                        )}
                      </td>
                      <td className="num">₹{b.total_rs.toLocaleString("en-IN")}</td>
                      <td className="num">₹{b.paid_rs.toLocaleString("en-IN")}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="row small muted" style={{ justifyContent: "space-between", gap: 12 }}>
              <span>
                Billed <b style={{ color: "var(--ink)" }}>₹{Number(ledger.totals.due_rs).toLocaleString("en-IN")}</b> ·
                Outstanding <b style={{ color: "var(--danger)" }}>₹{Number(ledger.totals.outstanding_rs).toLocaleString("en-IN")}</b>
              </span>
            </div>
          </>
        ) : null}
      </div>

      {/* payment */}
      <div className="card">
        <div className="card-title">
          <h2 style={{ fontSize: 15 }}>Record a payment</h2>
          <span className="muted small">applies to the oldest open bills · UPI</span>
        </div>
        <p className="muted small" style={{ marginTop: 0 }}>
          Posts against the student's oldest open bills and issues a numbered GST receipt.
        </p>
        <div className="inline-fields">
          <label className="field">
            <span>Amount (₹)</span>
            <input
              type="number"
              min={0}
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              style={{ width: 150 }}
            />
          </label>
          <span className="small muted" style={{ alignSelf: "center" }}>
            <IconRupee size={14} style={{ display: "inline", verticalAlign: -2 }} />{" "}
            {amount.toLocaleString("en-IN")} entered · {amount} paise
          </span>
          <button className="btn primary" onClick={recordPayment} disabled={paying || amount <= 0}>
            {paying ? "Posting…" : <><IconBanknote size={16} /> Record payment</>}
          </button>
        </div>
        {last && (
          <div style={{ marginTop: 14 }}>
            <span className="badge ok"><IconCheck size={12} /> Receipt {last.receipt_no}</span>
            <span className="muted small" style={{ marginLeft: 10 }}>
              applied to {last.applied_to_bills.length} bill(s) — load it in the receipt view below.
            </span>
            <div style={{ marginTop: 8 }}>
              <button className="btn" onClick={() => setReceiptNo(last.receipt_no)}>
                <IconSearch size={14} /> Open receipt
              </button>
            </div>
          </div>
        )}
      </div>

      {/* receipt view */}
      <div className="card">
        <div className="card-title">
          <h2 style={{ fontSize: 15 }}>Receipt view</h2>
        </div>
        <div className="inline-fields">
          <label className="field" style={{ flex: 1, minWidth: 200, maxWidth: 280 }}>
            <span>Receipt number</span>
            <input
              value={receiptNo}
              placeholder="FY2025/000199"
              onChange={(e) => setReceiptNo(e.target.value)}
              aria-label="Receipt number"
            />
          </label>
          <button className="btn" onClick={loadReceipt} disabled={receiptLoading || !receiptNo}>
            {receiptLoading ? "Loading…" : "Load"}
          </button>
          {last && !receiptNo && (
            <button className="btn ghost" onClick={() => setReceiptNo(last.receipt_no)}>
              use last: {last.receipt_no}
            </button>
          )}
        </div>

        {receipt && (
          <div className="receipt">
            <div className="receipt-head">
              <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                <span className="stat-icon" style={{ position: "static", width: 34, height: 34 }}>
                  <IconBanknote size={17} />
                </span>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{receipt.receipt_no}</div>
                  <div className="muted small">
                    FY {receipt.fiscal_year} · issued {String(receipt.issued_at).slice(0, 10)}
                  </div>
                </div>
              </div>
              <span className="badge ok"><span className="dot" /> paid</span>
            </div>
            <div className="table-wrap" style={{ maxHeight: 260, border: "none", boxShadow: "none" }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Head</th>
                    <th className="num">Amount</th>
                    <th className="num">GST</th>
                    <th className="num">Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {receipt.lines.map((l: any, i: number) => (
                    <tr key={i}>
                      <td>{l.head}</td>
                      <td className="num">₹{Number(l.amount_rs).toLocaleString("en-IN")}</td>
                      <td className="num">₹{Number(l.gst_rs).toLocaleString("en-IN")}</td>
                      <td className="num">{l.gst_rate}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="receipt-total">
              <span>Total paid</span>
              <span>₹{Number(receipt.total_rs).toLocaleString("en-IN")}</span>
            </div>
            {receipt.note && <div className="muted small" style={{ marginTop: 8 }}>{receipt.note}</div>}
          </div>
        )}

        {!receipt && receiptLoading && <div className="muted small" style={{ marginTop: 12 }}>Loading receipt…</div>}
        {!receipt && !receiptLoading && receiptNo !== "" && <div className="muted small" style={{ marginTop: 12 }}>No receipt with that number yet.</div>}
      </div>
    </div>
  );
}
