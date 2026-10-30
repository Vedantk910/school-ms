"""One-time production database bootstrap.

Applies Alembic migrations and seeds the full deterministic dataset into the
database named by ``SCHOOLMS_DATABASE_URL`` — designed to run **outside** the
container/serverless runtime (locally, on a VPS, or in a throwaway Python
shell) against a remote Postgres (e.g. Vercel Postgres).

Usage:
    SCHOOLMS_DATABASE_URL="postgresql+psycopg://user:pass@host/db" \
        python -m tools.bootstrap_db [--no-seed] [--retrain]

- ``--no-seed``    migrations only (use when you want to keep existing data).
- ``--retrain``    after seeding, train the at-risk + fee-default models and
                   materialise SHAP insights so the AI Insights page is alive.
- ``--include-portals``  seed the parent01 / stud0001 demo portal accounts too
                   (default: staff-only — Admin + Teacher logins, the prod posture).

Idempotent-ish: migrations are stamped/forwarded, and the seed drops +
recreates data tables (same code path as ``seeds.generate``).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-seed", action="store_true")
    ap.add_argument("--retrain", action="store_true")
    ap.add_argument("--include-portals", action="store_true",
                    help="also seed the parent01 / stud0001 demo portal accounts "
                         "(default: staff-only, Admin + Teacher)")
    args = ap.parse_args()

    url = os.environ.get("SCHOOLMS_DATABASE_URL")
    assert url and url.startswith("postgresql"), (
        "SCHOOLMS_DATABASE_URL must point at Postgres "
        "(e.g. postgresql+psycopg://...)"
    )

    # 1. schema via Alembic (the same path docker-compose `migrate` uses)
    from alembic.config import Config
    from alembic import command
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    print("== alembic upgrade head ==")
    command.upgrade(cfg, "head")

    # 2. deterministic full seed (550 students, ~240k attendance rows).
    # Production posture is staff-only (Admin + Teacher) logins; parent/student
    # portal accounts are opt-in via --include-portals for local/demo use.
    if not args.no_seed:
        print("== seeding full dataset ==")
        from seeds.generate import build
        counts = build(include_demo_portals=args.include_portals)
        counts.pop("seconds", None)
        print(json.dumps(counts, indent=2))

    # 3. optional: train models + materialise insights
    if args.retrain:
        print("== training ML models ==")
        from sqlmodel import Session
        from app.db import engine
        from app.ml.train import train_task
        with Session(engine) as s:
            for task in ("at_risk", "fee_default"):
                rep = train_task(s, task)
                print(f"{task}: auc={rep['gbr']['auc']} "
                      f"({rep['gbr']['n_eval']} eval rows, "
                      f"{rep.get('insights_stored', 0)} insights stored)")
        print("done — the AI Insights page now serves live SHAP explanations.")


if __name__ == "__main__":
    main()
