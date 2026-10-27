import { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth";

export default function Fees() {
  const { token } = useAuth();
  const [sid, setSid] = useState("1");
  const [ledger, setLedger] = useState<any>(null);
  const [receiptNo, setReceiptNo] = useState("");
  const [receipt, setReceipt] = useState<any>(null);
  const [amount, setAmount] = useState(100000);
  const [last, setLast] = useState<any>(null);

  useEffect(() => {
    api(`/fees/student-ledger/${sid}`, { token }).then(setLedger).catch(() => setLedger(null));
  }, [sid, token]);

  return (
    <div>
      <h1>Fees &amp; Billing</h1>

      <div className="card">
        <h2>Student ledger</h2>
        <label className="small">
          <span className="muted">Student ID</span>
          <input value={sid} onChange={(e) => setSid(e.target.value)} />
        </label>
        {ledger && (
          <>
            <table className="table">
              <thead>
                <tr>
                  <th>Installment</th>
                  <th>Due</th>
                  <th>Status</th>
                  <th>Total</th>
                  <th>Paid</th>
                </tr>
              </thead>
              <tbody>
                {ledger.bills.map((b: any) => (
                  <tr key={b.installment}>
                    <td>{b.installment}</td>
                    <td>{b.due}</td>
                    <td>
                      {b.waived ? <span className="badge waived">waived</span> : b.status}
                    </td>
                    <td>₹{b.total_rs}</td>
                    <td>₹{b.paid_rs}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="muted small">
              Billed ₹{ledger.totals.due_rs} · Outstanding{" "}
              <b>₹{ledger.totals.outstanding_rs}</b>
            </div>
          </>
        )}
      </div>

      <div className="card">
        <h2>Post a payment (demo)</h2>
        <p className="muted small">Applies against the student's oldest open bills and issues a numbered GST receipt.</p>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(Number(e.target.value))}
            style={{ width: 140 }}
          />
          <span className="muted small">₹{(amount / 100).toLocaleString()}</span>
          <button
            className="btn primary"
            onClick={() =>
              api("/fees/payments", {
                token,
                method: "POST",
                body: { student_id: Number(sid), amount_paise: amount, mode: "upi" },
              })
                .then(setLast)
                .catch(() => {})
            }
          >
            Record payment
          </button>
        </div>
        {last && (
          <div className="muted small">
            Receipt <b>{last.receipt_no}</b> applied to{" "}
            {last.applied_to_bills.length} bill(s). View below.
          </div>
        )}
      </div>

      <div className="card">
        <h2>Receipt view</h2>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <input
            value={receiptNo}
            placeholder="FY2025/000199"
            onChange={(e) => setReceiptNo(e.target.value)}
          />
          <button
            className="btn"
            onClick={() =>
              api(`/fees/receipt/${encodeURIComponent(receiptNo)}`, { token })
                .then(setReceipt)
                .catch(() => setReceipt(null))
            }
          >
            Load
          </button>
        </div>
        {last && !receiptNo && (
          <button className="btn ghost" onClick={() => setReceiptNo(last.receipt_no)}>
            load last: {last.receipt_no}
          </button>
        )}
        {receipt && (
          <div className="receipt">
            <div className="receipt-head">
              <b>{receipt.receipt_no}</b>
              <span className="muted small">FY {receipt.fiscal_year} · issued {receipt.issued_at.slice(0, 10)}</span>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Head</th>
                  <th>Amount</th>
                  <th>GST</th>
                  <th>Rate</th>
                </tr>
              </thead>
              <tbody>
                {receipt.lines.map((l: any, i: number) => (
                  <tr key={i}>
                    <td>{l.head}</td>
                    <td>₹{l.amount_rs}</td>
                    <td>₹{l.gst_rs}</td>
                    <td>{l.gst_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="receipt-total">Total ₹{receipt.total_rs}</div>
            <div className="muted small">{receipt.note}</div>
          </div>
        )}
      </div>
    </div>
  );
}
