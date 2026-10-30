# Deployment Runbook

First deploy on a VPS (any Ubuntu/Debian with Docker + Compose plugin), or locally.

## 1. Prerequisites

```bash
# Docker + compose plugin (Docker ≥ 20.10). On a VPS:
curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker
```

## 2. Configure

```bash
cp .env.example .env
# edit .env:
#   SCHOOLMS_JWT_SECRET  -> a long random string (required in production)
#   SCHOOLMS_LLM_BACKEND -> demo (default, offline) | ollama | openrouter
python -c "import secrets; print(secrets.token_hex(32))"   # generate a JWT secret
```

## 3. Migrate the schema (first deploy + every schema change)

```bash
docker compose up -d --build db      # start Postgres first
docker compose --profile tools run --rm migrate    # alembic upgrade head
```

On a **fresh** database this creates all 27 tables. On an **existing**
database it only applies pending migrations (additive, data-safe).

## 4. Build & launch the app

```bash
docker compose up -d --build         # api + web
docker compose logs -f api           # wait for "Application startup complete"
```

## 5. Seed the database (first deploy only)

```bash
docker compose --profile tools run --rm seed
# prints a volume report: ~550 students, 240k attendance rows, ~9.6k bills
```

Do NOT re-run against a populated production DB — it drops and recreates all
tables. For a fresh copy of the demo dataset, that is the intended behavior.

## 6. Train the ML models (first deploy only)

```bash
# 1) get an admin token via the API
TOK=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2) train both models + materialize SHAP insights (~1-2 min)
curl -X POST "http://localhost:8000/api/v1/ai/train?kind=all" \
     -H "Authorization: Bearer $TOK"
```

Trained artifacts persist in the `artifacts` named volume; rebuilding the
container does not wipe them.

## 7. Verify

```bash
curl http://localhost:8080/healthz          # web tier -> ok
curl http://localhost:8000/healthz          # api tier
# app:            http://<host>:8080       (logins: admin/admin, teach01/teacher)
# swagger:        http://<host>:8000/docs
```

## V1 production hardening

What ships with the app so a V1 deploy is hardenable without a separate
gateway or tooling:

### TLS — Caddy front

The compose stack ships a `caddy` service under the `tls` profile:

```bash
# CADDY_DOMAIN in .env: empty → defaults to localhost:8081 (Caddy's internal
# CA); a real domain → automatic HTTPS (ACME).
docker compose --profile tls up -d caddy
```

- Config: `caddy/Caddyfile` — routes `/api/*` → `api:8000`, `/` → `web:80`.
- Host ports: `${CADDY_HTTPS_PORT:-443}` and `${CADDY_HTTP_PORT:-80}`.
- State: `caddy_data` (certs/CA) and `caddy_config` named volumes.

### Backups — scripts/backup.sh & scripts/restore.sh

```bash
# nightly dump (02:00 cron on the VPS; sample line is in the script header):
0 2 * * * /path/to/school-ms/scripts/backup.sh
```

- Dumps to `backups/schoolms-<timestamp>.sql.gz`, verified with `gzip -t`;
  retention keeps the newest `${BACKUP_KEEP:-14}` archives, older ones pruned.
- Restore: `bash scripts/restore.sh <archive>` — requires typing `restore`
  to confirm; **overwrites** the target database.

### Gateway (SMS comms) — shipped

The outbox gateway lives in `backend/app/comms.py` + `routers/comms.py`:

```bash
# dev/default: offline, zero-cost (writes delivery records, no network)
SCHOOLMS_COMMS_BACKEND=log

# real dispatch: point at your SMS/WhatsApp HTTP gateway
SCHOOLMS_COMMS_BACKEND=sms
SCHOOLMS_SMS_BASE_URL=https://your-gateway.example
SCHOOLMS_SMS_API_KEY=...
SCHOOLMS_SMS_CHANNEL=sms      # or whatsapp
# drain the queue (admin-only), optionally cost-capped per batch:
curl -X POST http://localhost:8000/api/v1/comms/drain \
     -H "Authorization: Bearer $TOK" -H "Content-Type: application/json" \
     -d '{"cost_cap_paise": 50000}'
```

Dispatch is **consent-gated** (guardian-targeted sends only fire when the
DPDP consent flag is set; messages without consent are marked
`rejected_no_consent`) and **cost-capped** (`cost_cap_paise` stops the batch;
the rest stays queued for the next drain). Status: `GET /api/v1/comms/status`.

### Secrets checklist

- [ ] `SCHOOLMS_JWT_SECRET` is a real, high-entropy 32+ byte value (e.g.
      `python -c "import secrets;print(secrets.token_hex(32))"`) — not the
      `dev-secret-change-me` placeholder.
- [ ] Real Postgres credentials (the compose stack ships
      `schoolms`/`schoolms` for dev).
- [ ] `SCHOOLMS_SMS_API_KEY` present when the SMS gateway is enabled.
- [ ] `.env` stays gitignored; no secrets in compose files or the repo.

## Production notes

- **TLS / domain**: the stack now ships a Caddy front — see
  **V1 production hardening** above. Inside the container the web tier
  listens on :80 and the API is internal-only unless you keep the 8000
  port mapping. To stop exposing the API, remove the `ports` block from
  `api` and rely on the front's `/api` proxy.
- **Backups**: nightly gzip dumps via `bash scripts/backup.sh` (see
  **V1 production hardening**); the `pgdata` volume holds all state.
- **Update flow**: `git pull && docker compose up -d --build`. After *any*
  code change that touches `backend/app/models/`, generate and run a
  migration on the host before restarting the API:

  ```bash
  cd backend
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head            # local test DB
  cd ..
  docker compose --profile tools run --rm migrate   # apply in the deployment
  ```
- **Multi-student retraining**: `POST /api/v1/ai/train` is admin-gated and
  writes one model registry row per task; run it after any data refresh.

## Website deploy (no VPS needed)

For a public URL of the UI without a full-stack VPS, the repo ships a
**GitHub Pages** workflow (`.github/workflows/deploy-pages.yml`):

```
repo Settings → Pages → Source: "GitHub Actions"
```

After that, every push to `main` builds and publishes the site to
`https://<owner>.github.io/<repo>/`. Optionally trigger a manual "Deploy
website" run with `VITE_API_BASE` set to a live API URL so the static site
talks to a real backend. Same-origin also works when the stack runs behind
the Caddy front in a browser-reachable deploy.

The static Pages build has no server, so the **full product** (auth, data,
ML training, gateway dispatch) still needs the `docker compose` stack above;
Pages is the zero-infra way to showcase the UI + read-only flows.

## Known gaps (intentional, roadmap)

1. **No multi-worker load balancing** — single uvicorn process; fine at this
   scale (550 students).
2. **`POSTGRES_PASSWORD` in compose** — fine for a private VPS; use a
   secrets manager / env var for shared hosts.
3. **Trilingual UI + board topic-weight model** are V2 (decision D11).
4. **GitHub Pages hosts the UI only** — the app's data layer (DB, ML
   training, gateway) requires the compose stack; Pages is not a full
   backend host.

> Schema evolution is now handled by **Alembic** (`backend/alembic/`). The
> compose `migrate` service runs `alembic upgrade head` on a real Postgres,
> and the CI `postgres` job proves migrations + tests + seed on Postgres 16.

## Full-stack deploy on Vercel (zero-VPS option)

The repo also ships a **Vercel full-stack** deployment: the React app (built
from `frontend/`) **and** the FastAPI backend (as a Vercel Python function at
`/api`) on one project, with **Vercel Postgres** as the database. No VPS.

```
vercel project  : school-ms           (repo root)
database        : Vercel Postgres "school-ms-db" (Neon pooler endpoint)
API             : https://<host>/api/...   (function, api/index.py)
UI              : same host, SPA at /, assets at /assets/
```

**One-time bootstrap (run locally, once):**

```bash
cd backend
# 1) schema
SCHOOLMS_DATABASE_URL="<psycopg URL>" python -m tools.bootstrap_db --no-seed
# 2) full deterministic seed + train models + materialise SHAP insights
SCHOOLMS_DATABASE_URL="<psycopg URL>" python -m tools.bootstrap_db --retrain
```

Where `<psycopg URL>` is the Vercel Postgres connection string
(`postgresql+psycopg://user:***@...pooler...neon.tech/neondb` — get it via
`vercel env pull` or the Vercel dashboard; note the `+psycopg` scheme
SQLAlchemy needs, and `prepare_threshold=100` is already baked into `app/db.py`
for pooler safety).

**Vercel env vars (production scope, project `school-ms`):**

| Variable | Value |
|---|---|
| `SCHOOLMS_DATABASE_URL` | pooler URL above (with `+psycopg`) |
| `SCHOOLMS_JWT_SECRET` | `python -c "import secrets;print(secrets.token_hex(32))"` |
| `SCHOOLMS_CORS_ORIGINS` | the UI origins (comma-separated) |

**Behaviour notes:**
- `lifespan` runs `create_all` + Alembic stamp on function start — idempotent.
- Model **training** is intentionally *not* bundled into the serverless
  function (the ML stack would push the bundle past Vercel's 250 MB cap).
  `POST /api/v1/ai/train` returns a 501 with instructions; insights are served
  from the rows the bootstrap step materialises. To retrain, re-run
  `tools/bootstrap_db.py --retrain` locally and redeploy is not required —
  the data is in Postgres.
- The UI reads `VITE_API_BASE` when set, otherwise same-origin `/api/v1` —
  on this host that is correct as-is.
- Deployment protection: keep it **off** for a public demo; a gated deploy
  returns "Protected deployment" for anonymous visitors.

**Static-only hosts** (GitHub Pages, `frontend/` project on Vercel) remain
available for a UI showcase without a backend: `frontend/vercel.json` +
`frontend/public/404.html` make the SPA work on both.

## Render (always-on API, zero-VPS — recommended public demo)

The most reliable public option: one **always-on** Python service on Render
serving the API, reusing the seeded Vercel Postgres (Neon) database. No
serverless caps, no cold starts, full ML stack available.

```
render.yaml   (repo root — one-click Blueprint import)
service:      school-ms-api   (Python source runtime, health /healthz)
database:     EXISTING Neon Postgres — enter SCHOOLMS_DATABASE_URL when the
              blueprint deploy form prompts for it (pooler URL, +psycopg scheme,
              kept out of git; find it in .env.local)
```

**Setup (one-time, ~5 min):**
1. Render → New → **Blueprint** → connect the repo (the CLI `render blueprints
   deploy` works too once you've run `render login`).
2. When prompted for `SCHOOLMS_DATABASE_URL`, paste the Neon pooler URL with
   the `+psycopg` scheme (from `.env.local` → `DATABASE_URL`). The JWT secret
   is generated automatically by Render.
3. Wait for the build; hit `/healthz` on the service URL.

**Repoint the UI** (it already supports `VITE_API_BASE`):
- Vercel static host: `vercel env add VITE_API_BASE <render-url> --prod` + redeploy.
- GitHub Pages: run "Deploy website" manually with `VITE_API_BASE` set.
CORS is already configured in `render.yaml` (`SCHOOLMS_CORS_ORIGINS`) for both
hosted UI origins. Free Render plans idle after ~15 min (first request takes
~30 s); the "starter" plan is always-on.
