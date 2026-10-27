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
# app:            http://<host>:8080       (demo logins: admin/admin, ...)
# swagger:        http://<host>:8000/docs
```

## Production notes

- **TLS / domain**: put Caddy or nginx in front; the web tier listens on :80
  inside the container and the API is internal-only unless you keep the 8000
  port mapping. To stop exposing the API, remove the `ports` block from `api`
  and rely on the web tier's `/api` proxy.
- **Backups**: `docker compose exec db pg_dump -U schoolms schoolms > backup.sql`
  on a cron; the `pgdata` volume holds all state.
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

## Known gaps (intentional, roadmap)

1. **No multi-worker load balancing** — single uvicorn process; fine at this
   scale (550 students).
2. **`POSTGRES_PASSWORD` in compose** — fine for a private VPS; use a
   secrets manager / env var for shared hosts.
3. **Trilingual UI + board topic-weight model** are V2 (decision D11).

> Schema evolution is now handled by **Alembic** (`backend/alembic/`). The
> compose `migrate` service runs `alembic upgrade head` on a real Postgres,
> and the CI `postgres` job proves migrations + tests + seed on Postgres 16.
