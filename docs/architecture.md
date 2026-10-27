# Architecture & Execution Spec

Decisions from `docs/decisions.md` are assumed. This doc is execution-ready:
the build plan follows this layout exactly.

## 1. Repository Layout

```
school-ms/
├── README.md  deploy.md  docs/   # docs/: research, decisions, architecture, ml-eval
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI factory, router mounting, CORS, audit middleware
│   │   ├── config.py               # env-driven settings (pydantic-settings)
│   │   ├── db.py                   # engine, session factory, Base
│   │   ├── security.py             # argon2 hashing, JWT access/refresh issue+verify
│   │   ├── audit.py                # audit-log middleware/model
│   │   ├── models/                 # SQLModel tables (one file per domain)
│   │   │   ├── core.py             # AcademicYear, Board, Class, Section, Subject, Teacher, Holiday
│   │   │   ├── people.py           # User, Staff, Student, Guardian, Admission
│   │   │   ├── academic.py         # Attendance, Exam, ExamPaper, Mark, Result
│   │   │   ├── fees.py             # FeeHead, Bill, BillLine, Payment, Receipt
│   │   │   └── ai.py              # ModelRegistry, Insight, OutboxMessage
│   │   ├── schemas/                # Pydantic request/response (per domain)
│   │   ├── routers/                # auth, students, attendance, fees, exams, ai, admin
│   │   └── ml/
│   │       ├── features.py         # feature builders (attendance, fees, exam history)
│   │       ├── train.py            # GBDT + baselines, temporal split, metric report
│   │       ├── explain.py          # SHAP TreeExplainer, top-k reasons → Insight rows
│   │       └── registry.py         # load/serve/persist trained models (joblib + table)
│   ├── alembic/                    # migrations
│   ├── seeds/
│   │   └── generate.py            # deterministic synthetic dataset (D8)
│   ├── tests/
│   │   ├── test_auth.py test_students.py test_attendance.py test_fees.py
│   │   ├── test_exams.py test_ml_eval.py test_seed_repro.py
│   └── pyproject.toml             # fastapi, sqlmodel, sklearn, shap, argon2, pytest
├── frontend/
│   ├── src/
│   │   ├── api/ (typed fetch client)  auth/ (jwt store)  i18n/ (locale en.json)
│   │   ├── routes/  admin/ students/ attendance/ fees/ exams/ insights/ dashboard/
│   │   └── components/  (RoleGate, InsightCard, DataTable, ReceiptView, MarkGrid)
│   └── package.json               # react, vite, ts, tailwind, recharts, tanstack-query
├── docker-compose.yml             # db (pg16) + api + web + one-shot migrate/seed profile
├── Dockerfile.api  Dockerfile.web
├── .github/workflows/ci.yml       # lint → test → build images
└── README.md                      # demo accounts, cost table, walkthrough
```

## 2. Data Model (ERD, simplified)

```
Board 1── AcademicYear 1── Class 1── Section 1── *Student (enrollment)
Student 1── *Guardian (consent, DPDP fields) ; Student 1── 1User (student portal)
Student 1── *Admission (funnel status, RTE/EWS flag, U-Id, aadhaar_masked)
Section × AcademicYear 1── *Attendance (date, type P/A/L/H, leave_reason)
AcademicYear 1── *Exam (type external|internal, window) 1── *ExamPaper (subject, max)
Student×Exam×ExamPaper 1── 1Mark (theory, practical, total, grade, pass)
FeeHead (installment-aware, per class-level template) 1── *Bill (student×year×installment)
Bill 1── *BillLine (amount, gst_rate, gst) ; Bill 1── *Payment → *Receipt (sequential no, GST total)
Teacher 1── *Subject ; Subject appears in ExamPaper
ModelRegistry (name, version, metrics_json, artifact_path, trained_at)
Insight (student|class, kind, score, reasons_json[SHAP top-k], created_by_model)
OutboxMessage (template, audience, channel, lang, payload, sent_state)  # log-mode
```

Key engineering choices:
- **Amounts are integer paise**; dates are `date`/`timestamp` tz-aware;
  `Student.academic_year` is the enrollment key (student persists across years via
  `StudentYear` join table) — this is what makes 5-year ML features possible.
- **Receipt numbering** is a per-fiscal-year sequence with gap audit
  (finance-grade, portfolio detail).
- **Mark.grade** is computed, not stored, except final result (frozen on result publishing).

## 3. API Surface (REST, /api/v1)

```
POST /auth/login /auth/refresh /auth/me
GET/PATCH /students  POST /students/{id}/admissions
GET /students/{id}  (ledger, attendance %, exam history, insights included)
POST /attendance/register  (bulk day entry per section)  GET /attendance/summary
POST /fees/bills/generate  (installment × class template)
GET /fees/student-ledger/{sid}  POST /fees/payments  GET /receipts/{no}
GET /exams  POST /exams/{id}/marks (bulk grid)  GET /exams/{id}/results
GET /ai/insights/at-risk?class=…  (score + SHAP reasons)
POST /ai/train (admin)  → runs temporal split, writes ModelRegistry row + joblib
POST /ai/compose-notice (LLM adapter; demo mode returns templated, flagged output)
GET /admin/dashboards/overview  (enrollment, fee collection %, attendance, pass rate)
* all mutations → AuditLog (actor, resource, before/after hash)
```

RBAC: Admin (all), Teacher (own-section attendance/marks/notice), Parent
(own-child views + consent), Student (own views). JWT role claim; `RoleGate`
on frontend mirrors backend 403s.

## 4. ML Pipeline (the differentiator, spec'd precisely)

**Labels (both tasks, per student × academic-year):**
- `at_risk`: withholds ≥ 1 OR overall attendance < 70% OR internal assessment in
  bottom quartile (a composite "struggling-or-dropping" flag; withdrawal in prior
  year is a strong historical feature).
- `fee_default`: any bill of the year > 90 days overdue at as-of date.

**Temporal split:** train 2021-22…2024-25, eval 2025-26. No shuffling across years.

**Feature builders (features.py):**
- Attendance: % last-30/last-90 days, streaks, leave share, month-over-month delta.
- Fees: current dues, days-overdue max, installment count paid, historical default
  count.
- Exams: subject × last-2-exam score deltas, bottom-quartile subject count.
- Demographics/school: RTE/EWS, class, prior-year grade band (lagged → no leakage).

**Models:** `HistGradientBoostingClassifier` primary; baselines =
`LogisticRegression`, majority class. Report: AUC, F1, recall@top-decile,
confusion vs baseline; written to `docs/ml-eval.md` by `train.py` and asserted
in `test_ml_eval.py` (deterministic — fixed seed makes metrics reproducible).

**Explainability:** `shap.TreeExplainer` on the eval sample (capped n=2000 for speed),
per student-top-5 (feature, value, shap) stored in `Insight.reasons_json`. UI renders
"why flagged" cards — the SHAP story is the portfolio centerpiece.

## 5. Frontend Structure

- **Role-switcher** (dev convenience): pick Admin/Teacher/Parent/Student + demo user.
- **Dashboards**: one Recharts-heavy overview per role (charts from /admin/dashboards +
  module APIs via TanStack Query).
- **InsightCard**: SHAP top-5 horizontal bars + "advisory" disclaimer.
- **MarkGrid**: inline-editable marks table (teacher) → POST bulk.
- **ReceiptView**: printable GST-receipt component.
- i18n: `i18n/en.json` key-set; all copy routed through `t()` so MR/HI V2 is data.

## 6. Build Order

| Phase | Deliverable | Done-when |
|---|---|---|
| P0 | repo scaffold: pyproject, compose, CI, Dockerfiles, configs | `pip install -e .` + `pytest` boots empty |
| P1 | models + alembic init + seed generator (D8 volume) | seed runs deterministically, row counts hit target |
| P2 | auth + RBAC + audit + students/admissions endpoints + tests | 401/403 paths tested |
| P3 | attendance + fees (bills→payments→receipts, numbering, ledger) + tests | receipt gaps audited; ledger sums reconcile |
| P4 | exams/gradebook + results + dashboards endpoints | MSBSHSE grade math unit-tested |
| P5 | ml/features → train → registry → SHAP → insights endpoints + tests | deterministic metric report; SHAP reasons stored |
| P6 | frontend shell: role-gated routes, dashboards, MarkGrid, InsightCard, ReceiptView | dev server + API wired, role switch works |
| P7 | README, docs/demo-script, ml-eval report, CI green, compose up one-shot seed | fresh clone → `docker compose up` → demo login → full walkthrough |

**Sequencing note:** P2–P4 are parallelizable (different domains) but land sequentially
here; P5 depends on P1+P3 data; P6 after P2–P5 (needs real endpoints to query).

## 7. Non-Goals (keep build tight)
No multi-tenancy, no mobile apps, no real SMS/WhatsApp gateways, no payroll, no
timetable constraint solver — all V1+ (D11).
