"""Vercel serverless entrypoint for the School-MS FastAPI backend.

Vercel runs this file as a Python function at every ``/api/*`` path
(``api/index.py`` is the catch-all), mounting the ASGI app exported as
``app``. All application code lives under ``backend/``; this module only
wires the environment the serverless runtime provides:

- ``SCHOOLMS_DATABASE_URL`` — set in Vercel env, or auto-derived from the
  connection string Vercel Postgres injects as ``DATABASE_URL``.
- ``SCHOOLMS_JWT_SECRET`` — MUST be set in Vercel env for production.
- ``SCHOOLMS_ARTIFACT_DIR`` — model artifacts land in ``/tmp`` (the only
  writable path on Vercel); insights themselves are persisted to Postgres,
  so a cold start does not lose the demo.

Local dev is unchanged: ``uvicorn app.main:app`` under ``backend/``.
"""
import os
import sys
from pathlib import Path

# Make ``import app`` resolve to backend/app/ regardless of the function cwd.
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "backend"))

# --- serverless-specific wiring (harmless elsewhere) -------------------------
# Writable dir for joblib model artifacts (Vercel fs is read-only except /tmp).
os.environ.setdefault("SCHOOLMS_ARTIFACT_DIR", "/tmp/school-ms-artifacts")

# Vercel Postgres injects the pooler/direct connection string as DATABASE_URL.
if os.environ.get("DATABASE_URL"):
    os.environ.setdefault("SCHOOLMS_DATABASE_URL", os.environ["DATABASE_URL"])

# Heavy ML imports are deferred to the /ai/train route; keep app import light
# so cold starts stay fast.
from app.main import app  # noqa: E402,F401  (Vercel expects an ASGI `app` symbol)
