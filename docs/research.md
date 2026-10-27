# Research: End-to-End School Management System
**Target:** Private MSBSHSE-affiliated school, Maharashtra · 500–600 students · 5-year horizon
**Status:** landscape & domain research; decision-ready for feature selection

---

## 1. Executive Summary

Build a full-stack, AI-augmented School Management System (SMS) for a realistic
Maharashtra board (MSBSHSE) school of 500–600 students covering Pre-Primary → Std 10
(or 12), with:

- **Core ops:** student records, admissions, attendance, timetable, exams &
  gradebook, fees & receipts, staff, transport, library, events, notices,
  parent/student/staff portals, and export-grade reports.
- **AI layer (differentiator):** at-risk student early-warning, fee default
  prediction, exam performance diagnostics with topic-level insight,
  trilingual (English / Marathi / Hindi) communication assistant, and an
  LLM assistant for teachers (syllabus Q&A, question paper drafting,
  result summaries).
- **Portfolio positioning:** not just "another CRUD app" — a domain-aware,
  ML-augmented, production-shaped system with a realistic synthetic dataset
  (500 students × 5 academic years × monthly fees × fortnightly exams ×
  daily attendance ≈ 100k+ rows) and a live demo.

Estimated **feature scope**: 3 modules at MVP, 6–9 at V1, 12–15 at V2.
The rest of this doc maps the full landscape, so feature selection becomes
a prioritization exercise, not a discovery one.

---

## 2. Target School Profile (working assumptions — confirm or edit)

| Item | Assumption | Why it matters |
|---|---|---|
| Board | **MSBSHSE** (Maharashtra State Board, HSC Std 10) | Exam scheme, subjects, evaluation are board-specific — the core of domain awareness |
| Sections | Std 6–10 (boards school), 500–600 students, ~10–12 sections of 45–60 | Attendance, timetable, exams all scale with this |
| Medium | English-medium school, Marathi/Hindi optional subjects | Drives trilingual communication feature |
| Fee structure | Annual installments (e.g., 4–6/yr) + admission, exam, activity, transport, PTA/AGM levies; receipts with GST | Fees module is the finance core; realistic receipting matters |
| Admissions | Annual season + mid-year transfers; RTE/EWS quota (25% for affordable private schools) + UDISE code + U-Id reporting | Admissions funnel + compliance exports |
| Staff | 35–45 teaching + 15–20 non-teaching, payroll basics only (payroll deep is out of scope) | Staff module stays light |
| Transport | 6–10 routes, per-stop charges, conductor + driver | Classic SMS module |
| Data scale | 5 yrs × 550 students × 12 monthly bills + daily attendance + 4 exams/yr | ≈ 2–4M records — good for ML + dashboards |
| Languages | UI English; comms in 3 languages | AI trilingual feature is a showcase |

> **Note:** all data in the build will be **synthetic** (seeded, reproducible).
> Real student PII never enters the repo. DPDP Act 2023 (in force, Jan 2025)
> makes "synthetic demo, guardian-consent-first design" a good story in itself.

---

## 3. Maharashtra-Specific Context (this is where the "domain-aware" value lives)

### 3.1 Boards & curricula
- **MSBSHSE (HSC / Std 10, Marathi-medium)** and **MSBSHSE English-medium** —
  common pattern: comp subjects, English 100, Maths 40+60 (theory + internal),
  Science, Social Science, Marathi/Hindi optional, Computer optional.
- **CBSE / ICSE** schools differ — our system should model "board" as a
  configurable dimension, but hard-wire MSBSHSE as the default.
- **NEP 2020** alignment: competency-based, flexible entry-exit,
  multiple assessment modes (continuous & comprehensive, 20–30% weightage
  internal in boards) — model internal assessment as its own gradebook.

### 3.2 Exam & evaluation specifics (MSBSHSE)
- Annual pre-boards, final board (Feb–Mar window), results May–June.
- Evaluation scheme is public → **question bank generation and topic-weight
  prediction for board exams is a genuine, defensible AI feature** (competitors
  don't do it well).
- Result patterns: pass/fail cutoffs, compartment, division ranking,
  class rank — reporting templates differ from CBSE/ICSE.

### 3.3 Compliance & reporting
- **UDISE + U-Id** annual reporting (school-level census to state) — an
  "Export U-Id annual return" report is a differentiator no consumer SMS ships.
- **RTE / EWS seats** tracking (25% of intake at ₹3,000/yr fee for EWS).
- **Aadhaar / U-Id masking**: store only masked values; full Aadhaar storage
  is restricted under UIDAI rules — design the field that way from day one.
- **DPDP Act 2023**: minors' data requires guardian consent flow; log
  consent at onboarding; include a "Data Principal / Guardian" consent screen.

### 3.4 Fee & money specifics
- Maharashtra fee caps for *government-aided* schools don't apply to
  private unaided, but **MSBSHSE recognises fee transparency** — installments,
  waivers, scholarships (including merit-based board scholarship at
  HSC 85%+/90%+) are standard.
- PTA / AGM levies, transport charges by **route + stop**, mid-term
  exam fees, exam fee receipts for board candidates — all standard here.
- Receipt numbering: school-issued, sequential, GST-invoice format
  (₹ amount, HSN code where applicable, GSTIN fields on receipt).

### 3.5 Languages
- English, Marathi (Devanagari), Hindi (Devanagari). Notices, fee reminders,
  exam result letters, and the AI assistant should render Devanagari cleanly.

---

## 4. Competitive Landscape & Pricing (verify before launch; estimates below)

| Product | Type | Approx. price / school | Notes |
|---|---|---|---|
| **Fedena** (fetched live) | SaaS | Custom, usage-based (per their site); typical SaaS band ₹3–10k/mo | 50+ modules, strong, plugin model |
| **EduPort** | SaaS | ₹3–8k/mo band (typical India SMS SaaS) | ERP-flavoured, enterprise |
| **Scholdu / Gyanvii / V-School** | SaaS + apps | ₹2–7k/mo | Standard module set: attendance, fees, exams, transport |
| **Unibox / Amdesh CRM / Xamplus** | SaaS | ₹1.5–6k/mo | Lighter, cost-focused |
| **eSkooli / ProSchola** | SaaS | ₹2–5k/mo | |
| **OpenSIS / K-12 / open source (self-host)** | OSS | Free + hosting ₹1–3k/mo | Functional but no AI, dated UX |

**Two implications for us:**

1. **Cost bar:** a polished, low-cost, self-hostable system beats a ₹5k/mo
   SaaS subscription on TCO — this is the "lower cost" angle the user asked
   for.
2. **Differentiation bar:** none of the above do *board-aware* ML
   (at-risk prediction, fee default, board exam topic-weight analysis) or
   trilingual AI. **That's the gap and the portfolio hook.**

> ⚠ Pricing above are working estimates from domain knowledge; live pages
> didn't resolve in this session. Re-verify 3–5 of them (Fedena, EduPort,
> Scholdu, Gyanvii, Unibox) before writing a blog/demo copy.

---

## 5. Module Map (full landscape; to be prioritized during feature selection)

| # | Module | Core entities | Complexity | AI hook |
|---|---|---|---|---|
| 1 | **Students & Admissions** | Student, Admission, RTE slot, Guardian, U-Id, Class/Section | Medium | Admission-funnel analytics, dropout risk |
| 2 | **Academic (class/section/timetable)** | Class, Section, Subject, Teacher, Timetable (auto-fill) | Medium | Timetable conflict solver (constraint-based, not LLM) |
| 3 | **Attendance** | Daily register, type (present/absent/leave/holiday) | Medium | At-risk early warning, absence streak detection, leave auto-grant |
| 4 | **Exams & Gradebook** | Exam, Subject, Paper, Marks, Internal assessment, Result, Division | High (board-aware) | Topic-weight model for board prep, question generation |
| 5 | **Fees & Billing** | Fee head, Bill, Payment, Receipt, Installment, Waiver | High (finance-grade) | Default prediction, cashflow forecast, reminder triage |
| 6 | **Transport** | Route, Stop, Vehicle, Driver, Attendance | Low | — |
| 7 | **Staff / HR (light)** | Staff, Profile, Leave, Payroll input (not a full payroll) | Medium | — |
| 8 | **Communication & Notices** | Notice, SMS/WhatsApp template, Parent inbox | Medium | Trilingual AI composer + tone check |
| 9 | **Library** | Book, Member, Fine | Low | — |
| 10 | **Events & Activities** | Event, Club, Participation | Low | — |
| 11 | **Reports & Dashboards** | Per-role dashboards, export | Medium | "Insight card" (ML summary as a report widget) |
| 12 | **Portals (Parent / Student / Staff)** | Login, self-service views | Medium | AI assistant chat per role |
| 13 | **Security & Audit** | Roles, permissions, audit log | Medium | — |
| 14 | **AI Service** | Feature store, models, LLM API client | High | (all of it) |
| 15 | **Data / Seed** | Synthetic generator (5 yrs, 550 students, reproducible) | Medium | — |

---

## 6. AI Capability Map (with "wow factor" markers)

| Capability | Input | Model | Effort | Wow |
|---|---|---|---|---|
| **At-risk student early-warning** | Attendance, 3 prior exams, fee status | Logistic / GBDT, SHAP explainer | Medium | ⭐⭐⭐⭐ |
| **Fee default prediction** | Bill, payments, installments, seasonality | GBDT + seasonality features | Medium | ⭐⭐⭐⭐ |
| **Class-level exam diagnostics** | Marks by subject × exam × topic tag | Cohort analytics + LLM summary | Low–Med | ⭐⭐⭐ |
| **MSBSHSE board topic-weight model** | Public past boards (3–5 yrs) | Statistical + topic taxonomy | Med | ⭐⭐⭐⭐⭐ (genuine gap) |
| **Trilingual communication assistant** | Template + context | LLM with language routing | Med | ⭐⭐⭐ |
| **Teacher assistant** | Syllabus PDF + exam scheme | LLM RAG-lite | Med | ⭐⭐⭐⭐ |
| **Attendance anomaly / forecast** | Absence history, weather (free), exams | Forecasting (naive + SARIMA) | Low–Med | ⭐⭐ |
| **Admission funnel & dropout** | Admissions, withdrawals | Survival-ish / GBDT | Med | ⭐⭐⭐ |
| **Receipt OCR / document AI** | Uploaded receipts | LLM + vision (optional) | Med | ⭐⭐ (nice-to-have) |
| **Result letter generation** | Result data + student | LLM, 3 langs | Low | ⭐⭐ |

> Keep the **ML core interpretable** (SHAP, logistic regression baselines) —
> a school board / parent asks "why is this child flagged?" and SHAP answers
> it. That's both a good engineering call and a portfolio talking point.

---

## 7. Portfolio Positioning

**Narrative (one-liner):** "A production-shaped, AI-augmented school
management system for a real 500-student Maharashtra MSBSHSE school, with a
board-aware ML layer and trilingual communications, all on a reproducible
synthetic dataset."

**What makes this portfolio-grade vs "yet another CRUD app":**

- **Realism:** MSBSHSE board schema, receipt numbering, RTE/EWS tracking,
  UDISE/U-Id export — domain depth competitors skip.
- **ML that explains itself:** SHAP feature importance, baseline vs model,
  feature store, a clean `ai/` package — not a demo LLM wrap.
- **Reproducible synthetic data:** a `seed` command that regenerates 5 years,
  550 students, 4 exams/yr, monthly fees, daily attendance — ~2–4M rows,
  deterministic (seeded). Reviewers can run it.
- **Multi-role auth:** RBAC with 4 roles + audit log.
- **Trilingual UI** (Devanagari + Latin) — rare and memorable.
- **Live demo + GitHub + a short blog/README** = a deployable story.

**Artifacts to ship:**
- `README.md` (with demo links, screenshots, decision log)
- `02-architecture.md`, `03-runbook.md`
- GitHub repo (public) with CI
- A 5-minute Loom/screenshot demo: at-risk flag, fee default, result letter

---

## 8. Cost Strategy (the "lower cost" requirement)

| Area | Low-cost choice | Note |
|---|---|---|
| Hosting | **Free-tier VPS** (Hetzner/DO cheapest) or self-host on a Pi/VPS | Keep under ₹1–2k/mo |
| DB | PostgreSQL (free) | Fine at this scale |
| Frontend | Static Vite build, CDN | |
| LLM | **OpenRouter / Gemini free-tier** or a local Ollama model for demo; keep a thin LLM-adapter layer so it's swappable | Budget: 0–₹500/mo |
| SMS/WhatsApp | Demo mode (log-only) in dev; Twilio/TextLocal only for real run | Demo-mode keeps costs ₹0 |
| Email | Resend free tier (10k/mo) | Enough |
| Monitoring | Grafana Cloud free / Uptime Kuma | |
| **Total running cost** | **₹0 – ₹2.5k/mo** | vs ₹5–10k/mo for SaaS |

The key: **module-level LLM adaptation** so the system *works* without an LLM
(deterministic ML + template comms) and *upgrades* when one is attached. That
is also a clean architecture story.

---

## 9. Tech Stack Candidates

| Option | Stack | Strengths | Friction |
|---|---|---|---|
| **A (recommended)** | FastAPI + PostgreSQL + React (Vite) + scikit-learn + thin LLM adapter | ML-native, clean separation, fast API, modern, portfolio-friendly | Two front-ends if you want admin too |
| **B** | Django + DRF + Postgres + React | Batteries: auth, admin, ORM, audit out of the box | DRF adds ceremony; ML in Django is iffy |
| **C** | Next.js full-stack + Postgres + tRPC | One deployable, very polished UX | Less portable ML, heavier build |

**Recommendation: A** — FastAPI (API + jobs) + Postgres + React for the
3 portals + an `ml/` Python package + optional Ollama/OpenRouter. Rationale:
the *ML* is the differentiator, so the AI service should feel first-class, and
FastAPI + scikit-learn is the most reviewable combo.

---

## 10. Data Model Overview (core, to expand during architecture)

```
Board(1) ─ AcademicYear ─ Class/Section ─ Student
Student ─ Guardian(s) ─ Admissions ─ ClassSection
Student × AcademicYear ─ Attendance (daily, per type)
Student × AcademicYear ─ Marks (per Exam per Subject per Paper)
FeeHead ─ Bill ─ Payment ─ Receipt (numbered, GST fields)
Route ─ Stop ─ Vehicle ─ Student (transport)
Subject ─ Teacher ─ TimetableSlot
Exam ─ Paper ─ TopicTag (for board-weight model)
Notice ─ Template ─ Channel (SMS/WhatsApp/in-app)
```

Scale check: 550 students × 5 yrs × (300 attend days + 4 exams × 8 subjects +
12 bills + 30 payments) ≈ **3–4M rows**. Postgres handles this trivially;
the ML pipeline benefits from real volume.

---

## 11. Risks & Compliance (brief)

- **DPDP 2023 / minor data:** synthetic data in repo, guardian consent flow
  in UI, minimal PII, masked Aadhaar. (Design choice, not just legal.)
- **UIDAI:** no full Aadhaar storage; mask + hash only.
- **LPII / child images:** don't store in the repo, use S3-like object store
  with lifecycle, demo uses generated avatars.
- **SMS/WhatsApp vendor:** log-only mode by default; real gateway behind a
  flag (cost + consent reasons).
- **AI hallucination in exam-scheme claims:** label outputs "advisory, verify
  against official MSBSHSE documents."

---

## 12. Decision Points for Feature Prioritization

Feature selection decides, *in priority order*:

1. **MVP scope** — which 3 modules are "must-ship-now"?
   - My suggestion: Students & Admissions, Attendance, Fees & Billing, Exams &
     Gradeboard (4, slightly more than 3, but these are the spine).
2. **AI: real ML vs mocked** —
   - My suggestion: **real, deterministic** GBDT/logistic models for
     at-risk + fee default (trainable on synthetic seed, SHAP explained).
     LLM features: adapter-based, **log-only demo mode** (no live API in CI).
3. **Languages: 3 vs 1** — 3 (EN/MR/Hi) is the differentiator; 1 is
   faster. Suggest **1 at MVP (English), trilingual at V2** to ship faster.
4. **Frontend count** — one unified React app with role-based views, or
   3 separate portals? Suggest **one app, role-gated views** (less code,
   better portfolio cohesion).
5. **Board schema depth** — full MSBSHSE-accurate (subjects, weightages,
   topic taxonomy) or generic? Suggest **board-accurate for HSC Std 10**
   (that's the differentiator), generic for Std 6–9.
6. **Hosting target** — self-host (free-tier VPS) vs SaaS demo (Railway).
   Suggest self-host VPS + Docker for the cost story.

---

## 13. Sources & Verification

- **Fedena** (fedena.com) — module list verified live (50+ modules, plugin
  pricing).
- Pricing figures for EduPort / Scholdu / Gyanvii / Unibox / eSkooli are
  **estimates from domain knowledge** (SaaS band ₹1.5–10k/mo); **re-verify
  before publishing** any comparison in the README/blog.
- MSBSHSE scheme / evaluation: from public knowledge of HSC 10 evaluation;
  **verify against official MSBSHSE exam scheme PDF** before hard-coding
  topic weights in the board-weight model.
- NEP 2020 / DPDP 2023 / UIDAI: from public regulatory summaries; verify
  current status before launch copy.
