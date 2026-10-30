# School-MS — End-to-End, AI-Powered School Management System

A production-shaped, **AI-augmented school management system** for a realistic
550-student **MSBSHSE** (Maharashtra State Board, Std 6-10) school, running on a
fully reproducible synthetic dataset.

> Portfolio one-liner: *"A production-shaped, AI-augmented SMS for a real
> 550-student MSBSHSE school, with board-aware ML and interpretable insights,
> all on a reproducible synthetic dataset."*

## What makes this portfolio-grade (not "another CRUD app")

| Area | Detail |
|---|---|
| **Domain depth** | MSBSHSE board schema, HSC Std 10 theory/practical split (e.g. Maths 40+60), grade bands & division math, numbered **gap-audited GST receipts**, RTE/EWS seat flags, DPDP-2023 guardian-consent fields, masked Aadhaar |
| **Real ML** | GBR at-risk & fee-default models, **temporal train/eval split** (no cross-year leakage), **SHAP top-5 explanations** stored per student, versioned model registry, deterministic metric report (`docs/ml-eval.md`) |
| **LLM adapter** | Swappable LLM layer (demo / Ollama / OpenRouter) for trilingual-able notice composition; **demo mode runs fully offline** at zero cost |
| **Reproducible data** | One command regenerates **240k attendance rows, 51k marks, 9.6k bills, 7.5k receipts** across 5 academic years, deterministically (seed 42) |
| **Multi-role auth** | JWT RBAC for Admin/Teacher/Parent/Student + tamper-evident audit log |
| **V1.1 modules** | Transport (routes/stops/stop-charge revenue), Library (loans + late fines), Events/clubs, **Staff HR + payroll** (unpaid-leave deduction math), **deterministic timetable constraint solver** |
| **Production hardening** | Consent-gated + cost-capped SMS/WhatsApp gateway, Caddy TLS front, nightly pg backups + restore, secrets checklist, **full-stack on Vercel** (FastAPI serverless + Vercel Postgres) and GitHub Pages |
| **Cost story** | Self-hosts for **≤ ₹2.5k/mo** (VPS + Postgres + offline LLM) vs ₹5-10k/mo SaaS competitors |

## Architecture

```
frontend/   React 18 + TS + Vite, role-gated SPA (Recharts dashboards,
            SHAP InsightCard, printable GST receipt view)
              │  /api/v1
backend/      FastAPI + SQLModel + Postgres/SQLite
  ├─ models/   core, people, academic, fees, ai + v1.1 (transport, library,
  │           events, staff, timetable) — ~39 domain tables
  ├─ routers/  auth, students, attendance, fees, exams, events, transport,
  │           library, staff, timetable, comms, ai, admin
  ├─ ml/       features.py (leak-safe builders), train.py (GBR+baselines),
  │           explain.py (SHAP), registry + insight persistence
  ├─ comms.py  consent-gated, cost-capped outbox gateway (log/sms providers)
  ├─ timetable_solver.py  deterministic greedy+backtrack weekly scheduler
  ├─ llm.py    LLM adapter (demo default, Ollama/OpenRouter optional)
  ├─ alembic/  schema migrations (initial + v1.1 module tables)
  └─ seeds/    deterministic synthetic dataset generator
```

**Docs:** `docs/research.md` (landscape), `docs/decisions.md` (feature
selection), `docs/architecture.md` (execution spec), `docs/ml-eval.md`
(ML report).

## Quick start (no Docker needed)

### 1. Backend (API + data + ML)

```bash
cd backend
pip install -r requirements.txt        # or: pip install -e .
python -m seeds.generate               # seeds the SQLite DB (240k attendance rows, ~20s)
uvicorn app.main:app --port 8000      # API at http://localhost:8000/docs
```

To train the ML models and populate the insight engine:

```bash
# log in as admin (password "admin"), then:
curl -X POST "http://localhost:8000/api/v1/ai/train?kind=all" -H "Authorization: Bearer <token>"
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173  (proxies /api to :8000)
```

**Logins** (password = role name): `admin/admin`, `teach01/teacher`,
`stud0001/student`. The guardian demo login `parent01` is disabled in
production (`seeds/generate.py include_parent=False` default; re-enable with
`--include-parent`).

### 3. Regenerate the ML evaluation report

```bash
cd backend
python -m tools.make_ml_eval   # writes ../docs/ml-eval.md
```

## With Docker

The full first-deploy runbook (configure → build → seed → train → verify,
plus TLS/backups/update notes) is in **[deploy.md](deploy.md)**.

```bash
cp .env.example .env          # set SCHOOLMS_JWT_SECRET
docker compose up -d --build db
docker compose --profile tools run --rm migrate   # alembic upgrade head
docker compose up -d --build          # api + web
docker compose --profile tools run --rm seed      # one-time data seed
```

Optional extras (full details in **[deploy.md](deploy.md)**):

- **TLS front** — `caddy/Caddyfile` + the `caddy` compose service under the
  `tls` profile: `docker compose --profile tls up -d caddy`
  (set `CADDY_DOMAIN` in `.env`; empty defaults to `localhost:8081`).
- **Nightly backups** — `bash scripts/backup.sh` (writes
  `backups/schoolms-<timestamp>.sql.gz`, keeps the newest 14 by default);
  restore with `bash scripts/restore.sh <archive>`.

## Tests

```bash
cd backend
python -m pytest             # 72 tests across 14 files
```

The suite covers: auth + RBAC 401/403 paths, student ledger & receipt gap-audit,
exam grade computation, deterministic ML metrics (GBR vs logistic vs majority),
LLM demo composer, **seed reproducibility** (two runs → identical row hashes), and
the five V1.1 modules (transport, library, events, staff+payroll, timetable
solver) plus the comms gateway (consent gate + cost cap). CI additionally runs
the same tree on **Postgres 16** (migrate + full seed + full suite) and builds
both Docker images.

## The AI layer, explained

**At-risk early warning** — predicts a student will withdraw / sit below 70%
attendance / fall in the bottom quartile of Internal-1 scores. Features are
computed **as-of 30 November** of each year (no year-end leakage):
first-half & recent-90-day attendance, longest absent streak, low-mark subject
count, prior-year at-risk flag, prior grade band, RTE/EWS, dues as of November.

**Fee default prediction** — predicts a student has any bill >90 days overdue
by year-end. Trained with a strict temporal split, evaluated on 2025-26, and
each flagged student gets **SHAP top-5 reasons** (e.g. `dues_nov ↑`,
`prior_default_flag ↑`) — the explainer that a counsellor can actually act on.

Because the dataset is synthetic with a strong archetype signal, the eval AUC
is near-perfect; the transferable value is the **pipeline** (leak-safe features,
baselines, SHAP, reproducible evaluation), which carries to real data.

## Design decisions worth a look

- **Board-awareness** — subjects, theory/practical splits, and grade bands are
  data (`SubjectScheme`), not code; MSBSHSE is hard-wired, other boards plug in.
- **Low-cost by design** — deterministic LLM demo mode, log-only message outbox,
  SQLite dev / Postgres prod, static Vite build. The "lower cost" requirement
  is an architectural property, not a price tag.
- **DPDP 2023** — minor data is synthetic; guardian consent is a first-class
  field; Aadhaar is stored masked only.
- **Finance-grade receipts** — sequential per-fiscal-year numbering with a
  gap-audit endpoint (`GET /fees/receipts/gap-audit`) that flags missing numbers.

## V1.1 shipped — what a real school can run today

Everything a single school deployment needs:
- **Full operations**: students/admissions, attendance, fees + GST receipts,
  exams + gradebook, transport, library, events, staff + payroll, timetables
- **Insight layer**: at-risk + fee-default ML with SHAP explanations, LLM
  notice composer, class dashboards
- **Production hardening**: consent-gated SMS gateway, TLS front, backups,
  secrets discipline, Alembic migrations, CI-verified Postgres deploys,
  **website via GitHub Pages** + full-stack via `deploy.md`

## V2 roadmap (not in this build)

U-Id/UDISE export, trilingual UI, board topic-weight exam model, admission
funnel / attendance forecasting ML, receipt OCR, multi-tenancy, PTA portal,
mobile apps.

## Repository layout

```
school-ms/
├── README.md  deploy.md  docker-compose.yml  vercel.json
├── api/       (index.py — FastAPI app mounted as the Vercel serverless function)
├── caddy/     (Caddyfile — TLS reverse-proxy front, "tls" profile)
├── scripts/   (backup.sh, restore.sh — nightly Postgres dumps + restore)
├── docs/      (research, decisions D14/D15, architecture, ml-eval, sms-research)
├── .github/workflows/  (ci.yml: lint/test/Postgres/images + deploy-pages.yml)
├── backend/   (FastAPI + ML + comms gateway + 5 v1.1 modules + alembic + 72 tests
│               + tools/bootstrap_db.py — one-time migrate/seed/retrain for Vercel Postgres)
└── frontend/  (React SPA; same build serves Vercel + GitHub Pages; vercel.json in-tree)
```
