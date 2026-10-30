"""One-shot: disable parent/student logins in a live database.

After the Admin + Teacher-only finalisation, the seeded parent01 / stud0001
portal accounts must not sign in on the hosted app. This script marks those
rows inactive so /auth/login rejects them (verify_password still runs but
``active`` gates the login). Admin and teacher accounts are untouched.

Idempotent — safe to re-run; it only reports on re-runs.

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
    with eng.connect() as conn:
        rows = conn.execute(
            text("UPDATE app_user SET active = FALSE "
                 "WHERE role IN ('parent','student') AND active = TRUE")
        ).rowcount
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
