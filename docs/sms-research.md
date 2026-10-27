# Research: SMS Notifications for School-MS (Step 1)

**Status:** research only — no vendor chosen, nothing procured.
**Date:** 2026-10-27.
**Scope:** how transactional SMS should work for this product, which vendors fit, what
Maharashtra/Indian regulation imposes, and what it costs. Feeds Steps 2–4 (provider
integration, template/consent design, deployment).

Every figure below is an **estimate from domain knowledge**, not a live quote. Vendor
pricing pages were unreachable at the time of writing (see §10). Re-verify before any
commitment, and treat the price table as a decision aid, not a procurement document.

---

## 1. Executive summary

- **The gateway abstraction already shipped** (`backend/app/comms.py`) is the right
  shape: provider-swappable, consent-gated, cost-capped, and defaulting to a zero-cost
  offline `log` backend. Step 2 should *extend* it, not replace it.
- **Two live SMS channels matter for a school**: transactional/utility SMS (receipts,
  fee reminders, attendance alerts, exam results) and marketing/OTP SMS. School traffic
  is overwhelmingly the first kind. Transactional SMS is also the **cheapest** category
  in India — roughly **₹0.10–0.20 per SMS** on a small-volume plan.
- **DLT is the real onboarding barrier, not the code.** In India you cannot send
  commercial transactional SMS without a registered DLT entity, a registered sender
  header (head number), and every message template pre-approved against a specific
  template ID. This takes **days to weeks** and needs the school's own GSTIN and PAN.
- **The school is a legitimate "transactional" sender** for most traffic (fee receipts,
  attendance, exam results) — but the classification is decided by the template content
  and the DLT category, so templates must be written to that rule, not to a marketing
  template. Misclassification is the single most common reason Indian schools get
  templates rejected or accounts suspended.
- **WhatsApp is a serious second channel** and likely what guardians actually prefer
  for results and fee statements. It is more expensive (roughly **₹0.35–0.80** per
  template message, conversation-initiated) and needs its own DLT/brand approval, but it
  has far better read rates.
- **Recommendation:** ship with `log` backend, integrate **one** SMS vendor behind the
  existing `CommProvider` protocol, add **DLT template IDs** as first-class data, and
  defer WhatsApp to a second provider behind the same interface.

---

## 2. What the system already has (the integration surface)

| Concern | Existing implementation | Gap for real SMS |
|---|---|---|
| Provider swap | `CommsProvider` Protocol + `LogProvider` + `HttpSmsProvider` (`app/comms.py`) | `HttpSmsProvider` posts a **generic JSON** to `{base_url}/send`. Real vendors need vendor-specific fields (sender ID, DLT template ID, route, unicode flag, DLT headers). Needs a per-vendor payload adapter. |
| Delivery state | `outbox_message.sent_state` = `queued \| sent \| delivered \| failed \| rejected_no_consent` | No **DLT reference / vendor message id / delivery receipt**. A real gateway returns a message id and later a DLR webhook. `sent` should mean "accepted by gateway", not "delivered". |
| Consent gate | `_recipient_authorized_guardian()` — blocks guardian sends without DPDP consent | Consent is per-guardian and boolean. Needs **per-channel** consent (SMS vs WhatsApp vs voice), a consent **timestamp + evidence**, and a withdrawal path that flips it off. |
| Cost cap | `cost_cap_paise` stops a batch; `HttpSmsProvider.cost_paise = 100` (₹1.00) | The ₹1.00 figure is a placeholder, **not** a vendor rate. Needs a real per-category rate + a spend ledger (see §7). |
| Languages | `lang` field on the outbox row; `D5` says English at MVP, EN/MR/HI in V2 | SMS needs **unicode** for Devanagari and GSM-7 for English. A single concatenated message ≠ one billable SMS — Devanagari costs ~2x segments. Must be handled before MR/HI ships. |
| Routing/queue | `drain_outbox()` — synchronous loop, admin-triggered via `POST /api/v1/comms/drain` | Synchronous drain of a large audience will exceed HTTP timeouts and gateway rate limits. Needs **batching, rate limiting, retry with backoff, and a background worker**. |
| Templates | `template` string on the row; `advisory` flag for LLM-composed content | **DLT template IDs are missing** — this is the single biggest schema gap (§5). |

---

## 3. The Indian regulatory reality (DLT + TRAI)

This section is what makes Indian SMS different from every other market and it drives
the design.

### 3.1 Why DLT exists
TRAI's **Commercial Communications Regulations (2021)** ended the open SMS market.
All commercial traffic (including business/transactional to customers) must now be
**registered**, and the chain of accountability is enforced through **Distributed
Ledger Technology (DLT)** platforms, each tied to a specific operator:

| DLT platform | Operators covered |
|---|---|
| **Jio (Jio Txn / Jio Messaging)** | Jio (+ most Indian routes) |
| **Videocon / Vodafone (VBS — Videocon Business Services)** | Vodafone Idea |
| **Airtel (Airtel DLT / Airtel Business)** | Airtel |
| **BSNL (BSNL DLT / TCCC)** | BSNL |

A message travels on different operators' networks, so in practice **the same content
is registered on each operator's DLT**, or you route through a gateway that handles the
cross-operator registration for you. Most gateways offer this as a managed service
(§6) — this is the main reason to use a gateway rather than talking to an operator
directly.

### 3.2 The three things you must register
1. **Entity** — the school, on DLT, with GSTIN and PAN. The school itself is the
   registered entity (not the software vendor; you cannot send as your vendor).
2. **Header / head number** — the 6-digit alphanumeric sender ID shown to the
   recipient (e.g. `SCHOOLMS`), registered by the entity on each operator DLT and
   linked to the entity. Alternatively a 10-digit virtual mobile number, which lets you
   receive replies.
3. **Templates** — every distinct message body, pre-approved against a template ID.
   A template covers a fixed pattern with placeholders (e.g. `Dear {guardian_name}, your
   fee of INR {amount} for {month} is due on {due_date}.`).

**Nothing goes out until all three are approved.** Lead time is typically **3–10
business days** for entity+header and **1–5 business days** per template batch.

### 3.3 Template categories (and why miscategorising hurts)
DLT categorises templates, and the price and the rules both follow:

| Category | Use | Typical rule |
|---|---|---|
| **Transactional / Utility (DVT)** | Receipts, OTPs, confirmations, alerts about a transaction the user initiated | Cheapest; allowed with DLT registration |
| **Promotional / Marketing (DVP)** | Advertising, offers, "come to our event" | Higher price; **no 9pm–9am**; needs sender header registered to the entity |
| **Service / Government / Emergency** | Railway, bank, gov't | N/A for a school |

For this product the honest split is:

- **Transactional/utility (DVT)** — fee receipt issued, payment confirmation, invoice
  generated, admission acknowledgement, exam result published, attendance alert, leave
  approval, transport route change, library due notice.
- **Promotional (DVP)** — "annual day invitation", "fee waiver campaign", "PTA
  meeting invite", "admission open for 2026-27".

**Trap:** guardians interact with a school, so a fee *reminder* looks promotional but is
usually justified as transactional only if it relates to an **existing, specific
obligation** (an unpaid bill already raised). A generic "our fees are due" blast is
promotional. When in doubt, register it as promotional — the cost difference is
roughly ₹0.05–0.10/message, and a suspended account costs far more.

### 3.4 Sending-window rules
Promotional traffic is prohibited between **9 pm and 9 am**. Transactional traffic is
exempt. A school sending at 8 am to working guardians is fine for transactional
messages; schedule anything promotional for after 9 am.

### 3.5 Consent and DPDP Act 2023
- The **Digital Personal Data Protection Act 2023** governs the school's processing of
  guardian personal data (name, phone, student data). Consent for the *data processing*
  and consent for *the channel* are related but distinct.
- Because students are **minors**, consent must come from the guardian. The codebase
  already has `guardian.consent_given` — the right shape, but it needs a timestamp,
  the channel it covers, and evidence of how it was obtained (signed form, app
  checkbox, SMS opt-in).
- Under DPDP, a guardian must be able to **withdraw consent** as easily as they gave
  it, and the notice purpose must be specified ("sending fee and academic notices to
  this mobile number").
- **Do not put the child's Aadhaar, U-Id, or any student identifier in an SMS body.**
  Use the admission number, or the guardian's own name. This is both a DPDP
  minimisation point and a DLT template rule (templates with personal data are
  sensitive; keep placeholders minimal).

---

## 4. Maharashtra specifics

- **Language.** Marathi is the working language of most Maharashtra households even in
  English-medium schools. Fee receipts, attendance alerts and exam results should go
  out in **Marathi by default** with an English option. Both are Devanagari/unicode,
  so GSM-7 optimisation does not apply — a 160-char Marathi message becomes
  **~70–80 characters per SMS segment** (70 for 16-bit unicode, per the concatenated
  SMS standard), i.e. roughly **2 segments** for a typical receipt message. Budget
  accordingly (§7).
- **Board context.** MSBSHSE result publication and school re-opening around the
  Feb–Mar board window and the May–June result window are the **two highest-volume SMS
  days** of the year. Both are transactional (result published for a specific student)
  and are the clearest justification for a transactional template.
- **Fee transparency expectations.** Fee notices in Maharashtra schools are expected to
  state the amount, the due date, and the components. Templates should carry
  `{amount}`, `{due_date}`, `{installment_no}`, `{receipt_no}` placeholders — this maps
  directly onto the existing `bill`/`receipt` tables, so a receipt SMS can be
  templated without any new data plumbing.
- **RTE/EWS.** Fee-waiver notices for RTE/EWS students are sensitive; the amount
  waiver must be stated carefully and is arguably transactional (it's a specific
  concession on a specific bill), but a "you are eligible for a scholarship" broadcast
  is promotional.
- **Language note on transport and lunch.** Maharashtra schools often run a mid-day
  meal scheme; a "meal not delivered / student absent from mid-day meal" message is
  transactional and is a genuinely appreciated alert.
- **No state-level SMS registration** is required beyond DLT + the school's own
  registration. There is no Maharashtra-specific SMS licensing layer, unlike some
  sectors (e.g. DMTND for elevators, or loan-advertiser RBI rules). The state-specific
  work is **content and language**, not extra regulatory filings.

---

## 5. Schema changes needed (feeds Step 2 and Step 3)

These are the concrete additions the research implies. They are listed as *requirements*
for the design, not as implemented work.

**On `outbox_message`:**
- `dlt_template_id` (nullable) — the approved DLT template this body was rendered
  against. Without it, no real send is possible.
- `provider_message_id` — the gateway's id, needed to reconcile the DLR.
- `sender_id` / `header` — the registered sender header used (may vary by
  registered route/operator).
- `segment_count` — billable segments for this body (matters for unicode).
- `provider` — which provider actually sent it (in case of failover/migration).
- `sent_state` refinement: `queued → submitted → accepted → delivered / failed /
  rejected_dlt / rejected_no_consent`. Note `accepted` ≠ `delivered`; delivery arrives
  later via the gateway's DLR webhook.

**On `guardian`:**
- `consent_sms` / `consent_whatsapp` booleans (channel-scoped, not one global flag).
  Note: `consent_given` and `consent_at` **already exist** (`app/models/people.py`),
  so the timestamp half of this is done — what is missing is the *channel* split and
  the evidence of how consent was obtained.
- `consent_source`, `consent_note` (DPDP evidence — how and under what stated purpose
  the guardian agreed).
- `phone_e164` — normalised E.164 phone; the current `phone` field is a free-text
  string and real gateways need `+91XXXXXXXXXX`. Also add `phone_verified` (an OTP
  round-trip is the only real verification).

**On a new `dlt_template` table:**
- `template_key` (stable internal key, e.g. `fee_receipt`), `dlt_template_id`,
  `category` (transactional | promotional), `body_en`, `body_mr`, `placeholders`,
  `approved_at`, `status` (draft | pending | approved | rejected).

**On a new `sms_spend_ledger` / spend tracking:**
- Per-period spend by template and category, so the cost cap is informed by real
  rates rather than the hardcoded ₹1.00.

---

## 6. Vendor landscape

Categories, not endorsements. All prices are **indicative** per-SMS in ₹, transaction
category, small volume.

| Vendor | Type | Indicative price/SMS | Strengths | Watch-outs |
|---|---|---|---|---|
| **MSG91** | Aggregator, DLT-managed | ~₹0.10–0.20 (txn), higher for promo | Very strong DLT support, per-operator registration handled, good APIs, free tier for early use, supports WhatsApp | Per-SMS cost at scale can beat others; read their per-route pricing carefully |
| **Gupshup** | Aggregator | ~₹0.10–0.25 | Huge operator reach, mature DLT tooling, strong WhatsApp Business API, good delivery reporting | Sales-led pricing — negotiate; volume tiers matter a lot |
| **Fast2SMS / MSG2SMS / Textlocal (Infobip)** | Budget aggregators | ~₹0.05–0.15 | Cheapest, good for high-volume transactional | Lower DLR fidelity, weaker compliance posture — verify DLT support explicitly before relying on it for fee receipts |
| **Exotel** | Cloud comms (voice+SMS+WhatsApp) | ~₹0.15–0.30 | Excellent WhatsApp + voice, clean API, good for schools (also handles missed-call and voice alerts) | More expensive for plain SMS; a bulk-SMS specialist would be cheaper |
| **Telnyx / Twilio (global)** | International | USD-based, usually ₹0.4+ | Strong APIs, easy sandbox | **Not DLT-native** — you still must register entity/header/templates on operator DLT yourself; higher cost. Poor fit for an India-first low-margin product |
| **Direct operator (Jio/Airtel/Vi)** | Operator-direct | ~₹0.12–0.30 | Best rates at very high volume | Requires your own DLT entity + per-operator registration and integration; enterprise onboarding — wrong shape for a school SaaS |

**Practical read:** for 550 students × ~3 messages/month ≈ **16,500 SMS/month ≈ ₹2–3k/month**
at transactional rates — small enough that the gateway's *DX* (how much DLT pain it
absorbs) matters far more than a ₹0.03 price difference.

**Selection criteria to apply in Step 2:**
1. **Does the gateway absorb DLT registration for our entity**, or must we do it per
   operator ourselves? (This is the single biggest differentiator for a school.)
2. Do they support **transactional category** pricing and **unicode** (Marathi)?
3. Do they provide **DLR webhooks** (delivery receipts) and **message-id reconciliation**?
4. Rate limits, and **retry semantics** on failure.
5. Whether the API can be called from a **self-hosted** backend in India (data
   residency / latency), and whether an **Indian entity** is needed to transact.

---

## 7. Cost model (estimates)

For the target school: **550 students**, ~3 messages/guardian/month in normal months.

| Scenario | Messages/mo | Rate | Monthly cost |
|---|---|---|---|
| Baseline (txn, GSM-7 English) | ~16,500 | ₹0.15 | ~₹2,500 |
| Baseline with Marathi (2 segments) | ~16,500 | ₹0.30 | ~₹5,000 |
| Exam-result peak (all students, 1 result SMS + 1 fee notice) | ~1,100 × 2 | ₹0.30 | ~₹700 (one month) |
| Marginal cost of adding WhatsApp results channel | ~550 | ₹0.60 | ~₹330 |

This sits against the stated cost target in `D10` (total runtime ≤ ₹2.5k/month). A
real-SMS deployment at the baseline pushes past that, so the **cost cap in
`drain_outbox` becomes a budget control, not just a safety valve** — the honest
positioning becomes "VPS ₹1–2k + SMS ₹2–5k = ₹3–7k/mo", still below the ₹5–10k/mo SaaS
competitors in `docs/research.md` §4, but no longer "₹2.5k total". That trade-off
should be stated plainly in the README rather than hidden.

**Cost levers:**
- Keep routine messages (fee reminders, attendance digests) to **one concise SMS** —
  a Marathi receipt with a long itemised breakdown will cost 2–3 segments.
- Batch per-guardian rather than per-student where the audience permits.
- Prefer **in-app** for anything not urgent; SMS is for things a guardian must act on.
- Use the cost cap as a **monthly budget**: drain with `cost_cap_paise` set to the
  remaining monthly allowance.

---

## 8. Recommended design (the input to Steps 2–4)

**Channel strategy (by message type):**

| Message | Channel | Category | Rationale |
|---|---|---|---|
| Fee receipt / payment confirmation | SMS (Marathi) | Transactional | Proof of payment; guardians expect it |
| Overdue fee reminder | SMS | Transactional (if tied to a raised bill) | Specific obligation |
| Exam result published | SMS + WhatsApp | Transactional | High-value, high-read; WhatsApp for the rich card |
| Attendance daily alert | WhatsApp, or in-app | Transactional | High volume, low urgency, low SMS willingness |
| Leave request status | SMS | Transactional | Time-sensitive |
| Transport route change / delay | SMS | Transactional | Time-sensitive, safety-relevant |
| Event invite, PTA notice, admission campaign | WhatsApp + in-app | Promotional | Needs the 9am–9pm window; SMS is poor ROI |
| OTP / login | SMS | Transactional | Vendor OTP flow, not ours |

**Provider architecture (extends the shipped code):**
- Keep `CommProvider` as the seam. Add a `DltSmsProvider` that renders a template
  against a **DLT template id**, sends vendor-specific fields, and maps the vendor
  response to `SendResult` with a `provider_message_id`.
- Add a **template registry** so message content is data, not code — required for DLT
  approval to be meaningful.
- Add a **background worker** for draining (with per-batch rate limiting and retry),
  keeping `POST /api/v1/comms/drain` as the admin trigger for a manual flush.
- Add a **DLR webhook** endpoint to move rows from `accepted` → `delivered`/`failed`.
- Keep `log` as the default backend so the demo, CI, and the existing
  `test_comms.py` suite keep working with zero network and zero cost.

**Consent (DPDP-aligned):**
- Channel-scoped consent with timestamp + source.
- The consent gate stays in `drain_outbox`, but must consult the *channel's* consent
  flag — a guardian who consented to WhatsApp has not consented to SMS.
- Provide a one-step "stop SMS" path that flips consent and suppresses the number.

**Ordering for Step 2 (integration):**
1. Vendor-neutral DLT template registry + schema changes (§5) — no vendor needed.
2. Pick one gateway per §6 criteria; implement `DltSmsProvider` for it.
3. Sender-id + template registration process documented (`docs/`), including the
   school's GSTIN/PAN requirement and the lead time.
4. DLR webhook + background drain.
5. WhatsApp as a second provider, same protocol.
6. Marathi templates + unicode/segment handling.

---

## 9. Open questions for the school (needs a human decision)

1. **Does the school send from its own name?** A registered header (e.g. `SCHOOLMS` or
   a school acronym) requires the school to complete DLT entity registration with
   GSTIN and PAN. If the school will not, the fallback is a **virtual 10-digit number**
   as sender — lower trust, and guardians may not recognise it.
2. **Marathi-first or English-first?** This is the single biggest cost and adoption
   decision (2x segment cost).
3. **Who pays for the SMS?** Bundled in the SaaS fee, or passed through per message?
   This determines whether the cost cap is a budget guard or a billing meter.
4. **WhatsApp in scope for V1?** It materially improves result-notice engagement but
   adds DLT/brand approval effort and cost.
5. **Which messages are genuinely transactional?** The school should sign off the
   category per template, since misclassification risks account suspension.
6. **Is the school willing to pay for a real gateway now, or run `log` through the
   pilot?** The pilot (log backend) is free and exercises every path except the
   network hop.

---

## 10. Sources & verification status

**Verified by reading this repository (ground truth):**
- `backend/app/comms.py` — provider protocol, consent gate, cost cap, drain loop.
- `backend/app/models/fees.py` — `outbox_message` fields and `sent_state` values.
- `backend/app/config.py` — `comms_backend`, `sms_base_url`, `sms_api_key`,
  `sms_channel`.
- `backend/tests/test_comms.py` — the acceptance bar the real provider must keep
  passing.
- `docs/decisions.md` — D9 (comms is MVP in-app + log; real vendor = V1), D10 (cost
  target), D12 (testing bar).
- `deploy.md` — the gateway's documented runtime contract.

**From domain knowledge — re-verify before launch:**
- All per-SMS prices and vendor capabilities in §6. Vendor pricing pages were not
  reachable when this document was written (network fetch was rate-limited), so **no
  figure here has been checked against a live pricing page**.
- DLT platform names, the 3–10 business-day approval lead times, the 9pm–9am window,
  and the 70/153/153 character segment rule for 16-bit unicode (Devanagari).
- The promotional-vs-transactional category boundary. This is the item most likely to
  have shifted and the one with the highest blast radius — confirm with the chosen
  gateway in writing before registering templates.
- DPDP Act 2023 consent requirements for minors' guardians.

**Must be confirmed with the school before registration:** legal name, GSTIN, PAN,
authorised signatory for DLT entity registration, and the sender header they want.
