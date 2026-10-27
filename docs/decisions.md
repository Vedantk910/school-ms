# Decisions (Feature Selection)

Locked 2026-07-26. These decisions make execution mechanical.

## D1 · Target profile
Private **MSBSHSE-English-medium** school, Std 6–10, **550 active students**, ~45 staff,
5 academic years of history (2021-22 → 2025-26), as-of date **2026-06-30** (full 2025-26
year complete → clean ML training/eval split).

## D2 · Board model
MSBSHSE HSC Std 10 is **board-accurate** (subjects, max marks, grade bands, pass rules,
paper split e.g. Maths theory 40 + practical 60). Std 6–9 and other boards use a
**generic configurable scheme**. Board is a data dimension, not a code fork.

## D3 · MVP scope (ship V0.1)
1. **Students & Admissions** — student/guardian records, admission funnel, class-section
   enrollment, U-Id + Aadhaar **masked**, RTE/EWS flags, DPDP guardian-consent fields.
2. **Attendance** — daily class/section registers, P/A/L/H types, holiday calendar,
   monthly %, streaks, leave requests.
3. **Fees & Billing** — fee heads, installment plans per class, generated bills,
   payments, **numbered receipts with GST breakup**, waivers, student ledger, aging.
4. **Exams & Gradebook** — exam calendar (2 external + 2 internal/yr), bulk mark entry,
   MSBSHSE grade computation, class/division aggregates, ranks, result sheets.
5. **AI Service** — at-risk early warning, fee-default prediction, class diagnostics
   (all interpretable + SHAP), LLM notice composer (demo mode).
6. **Shell** — RBAC (Admin/Teacher/Parent/Student), audit log, dashboards, one React app
   with role-gated views, Docker Compose, synthetic seed, CI.

## D4 · AI approach — **real ML + LLM adapter**
- ML: `HistGradientBoostingClassifier` (sklearn) for at-risk & fee default; **temporal
  split** (train 2021–24, eval 2025-26); baselines (logistic, majority) always reported;
  **SHAP TreeExplainer** top-k reasons stored with each insight; model artifacts in a
  versioned registry table + local store; batch retrain admin API.
- LLM: adapter protocol `AIService` → default `DemoLLM` (deterministic templates,
  zero cost, no network, "advisory" disclaimer); optional `OllamaLLM` / `OpenRouterLLM`
  via env. All LLM output labeled advisory + verified-sources note.
- Why: works fully offline/reproducible in CI (portfolio-grade engineering signal),
  upgrade path is a config flag, not a rewrite.

## D5 · Languages
**English at MVP.** All UI strings through a locale JSON (single key set) so trilingual
(EN/MR/HI Devanagari) in V2 is data, not refactor. Comms composer can emit language tags.

## D6 · Front-end — **one app, role-gated**
React 18 + TypeScript + Vite + Tailwind + TanStack Query/Router + Recharts.
Routes gated by JWT role; role switcher on demo login (dev-only convenience).

## D7 · Stack
| Layer | Choice |
|---|---|
| API | Python 3.11, FastAPI, Pydantic v2, SQLModel (SQLAlchemy 2.0) |
| DB | PostgreSQL 16 (docker-compose), Alembic migrations |
| ML | scikit-learn, SHAP, joblib, no GPU; in-process batch jobs |
| LLM | adapter; Ollama/OpenRouter optional, off by default |
| Web | React 18 + TS + Vite, served as static by Caddy in compose |
| Auth | JWT access (15m) + refresh (7d), argon2 hashes |
| Tests | pytest + httpx (API), pytest (ML metrics), ruff lint |
| CI | GitHub Actions: lint → test → build both images |
| Deploy | docker compose (db, api, web, migrate), free-tier VPS target |

## D8 · Data
Synthetic, **seeded deterministic** (`np.random.default_rng(42)`), no real PII, fixed
as-of 2026-06-30. Volume target ≈ **1M attendance + 100k marks + 15k bills + 40k payments**
(5 yrs × ~1,100 students incl. alumni). Correlated risk factors baked in (attendance
drop → late fees → withdrawal) so the ML has real signal + SHAP has real features to show.

## D9 · Comms
MVP channels: **in-app notices + log-mode sender** (writes to `outbox`, no real SMS/WhatsApp).
Gateway adapter interface reserved; real vendor = V1 (cost + consent reasons).

## D10 · Cost story (runtime)
VPS ₹0–2k/mo + Postgres same host + LLM off (demo mode) → **≤ ₹2.5k/mo total**
vs ₹5–10k/mo SaaS competitors. TCO argument in README.

## D11 · Out of scope for V0.1 (roadmap V1/V2)
Transport, library, events/clubs, staff HR/payroll, timetable auto-fill, U-Id/UDISE
export reports (stub API only), trilingual UI, board topic-weight exam model, admission
funnel ML, attendance forecasting, receipt OCR, PTA portal, multi-tenant, mobile apps.

## D12 · Testing bar
- API: ≥ 60% endpoint coverage on the 4 spine modules (happy + one authz failure each)
- ML: deterministic metric table (AUC/f1 vs baselines) asserted in tests
- Seed: reproducibility test (two runs → identical row hashes)
- Frontend: build passes; no runtime test framework in V0.1 (smoke = manual demo script)

## D13 · Portfolio artifacts (ship with code)
- `README.md`: 5-min walkthrough, demo accounts, cost table, screenshots
- `docs/decision-log.md` (this file), `docs/architecture.md` (03), `docs/demo-script.md`
- Deterministic ML evaluation report (`docs/ml-eval.md`, generated)
- GitHub repo + CI green + deployable compose file

## D14 · V1 hardening status
| Item | Owner file(s) | Status | Acceptance |
|---|---|---|---|
| Gateway | `backend/app/comms.py`, `routers/comms.py` | **shipped** | `test_comms.py` green — provider swap, consent gate, cost cap |
| TLS | `caddy/Caddyfile`, `docker-compose.yml` (caddy profile) | **shipped** | compose YAML parses; `docker compose --profile tls up` path documented |
| Backups | `scripts/backup.sh`, `scripts/restore.sh` | **shipped** | `bash -n` clean; retention + cron line documented |
| Secrets discipline | `.env.example`, `docker-compose.yml` | **shipped** | no secrets committed; `.env.example` carries the prod checklist |

## D15 · V1.1 modules status
| Module | Owner file(s) | Status | Acceptance |
|---|---|---|---|
| Transport | `models/transport.py`, `routers/transport.py` | **shipped** | `test_transport.py` green — stop ordering, revenue by stop, RBAC |
| Library | `models/library.py`, `routers/library.py` | **shipped** | `test_library.py` green — copy availability, 2000-paise/day fine |
| Events/clubs | `models/events.py`, `routers/events.py` | **shipped** | `test_events.py` green — upsert idempotency, mandatory no-shows |
| Staff HR + payroll | `models/staff.py`, `routers/staff.py` | **shipped** | `test_staff.py` green — unpaid-leave deduction math, audit rows |
| Timetable solver | `models/timetable.py`, `timetable_solver.py`, `routers/timetable.py` | **shipped** | `test_timetable.py` green — determinism, constraints 1-4, RBAC |
| Alembic v1.1 migration | `alembic/versions/82cdd9429902_*.py` | **shipped** | `alembic upgrade head` creates all 12 new tables |

> Full suite: **72 passing tests** on SQLite; CI additionally proves the same
> tree on Postgres 16 (migrate + full seed). The website deploys via GitHub
> Pages (`.github/workflows/deploy-pages.yml`); the full-stack stack is in
> `deploy.md`.
