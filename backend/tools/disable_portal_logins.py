"""One-shot: disable the seeded parent login in a live database.

After the staff-only finalisation, the seeded ``parent01`` guardian account
must not sign in on the hosted app. This script marks parent rows inactive so
/auth/login rejects them (``verify_password`` still runs, but ``active`` gates
the login). Admin, teacher and student accounts are untouched.

Idempotent — safe to re-run; on re-runs it just reports.

Usage (from the repo root, backend/ dir):
    SCHOOLMS_DATABASE_URL="postgresql+psycopg://..." \
        python tools/disable_portal_logins.py
"""
from __future__ import annotations

import os
import sys

from sqlalchemy import create_engine, text


def main() -> int:
    url = os.environ.get("SCHOOLMS_DATABASE_URL")
    if not url or url.startswith("sqlite"):
        print("SCHOOLMS_DATABASE_URL must point at the live Postgres DB")
        return 1

    eng = create_engine(url, pool_pre_ping=True)
    with eng.begin() as conn:  # transactional: the UPDATE is committed
        rows = conn.execute(
            text("UPDATE app_user SET active = FALSE "
                 "WHERE role = 'parent' AND active = TRUE")
        ).rowcount
    with eng.connect() as conn:
        total = conn.execute(
            text("SELECT username, role, active FROM app_user "
                 "ORDER BY role, username")
        ).fetchall()

    print(f"deactivated {rows} login(s). app_user now:")
    for username, role, active in total:
        print(f"  {username:<10} {role:<8} active={active}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
