"""SQLModel declarative base + engine/session factory.

Runs on SQLite for local dev/test and PostgreSQL under docker-compose, both
first-class, selected by ``settings.database_url``.
"""
from sqlmodel import SQLModel, Session
from sqlalchemy.engine import create_engine
from sqlalchemy.pool import StaticPool

from app.config import settings


class Base(SQLModel):
    """Declarative base shared by all table models."""
    pass


def _make_engine(url: str):
    if url.startswith("sqlite"):
        # StaticPool keeps a single connection; fine for in-memory/test use.
        connect_args = {"check_same_thread": False} if ":memory:" in url else {}
        return create_engine(url, connect_args=connect_args, poolclass=StaticPool)
    # Postgres. Vercel Postgres / Neon route through a pgbouncer pooler that
    # caps cached (prepared) statements; psycopg's default cache of 512 would
    # hit that on a busy app. prepare_threshold=100 keeps the planner honest
    # (plain text protocol past 100 repeats, so nothing over the wire is
    # ever "prepared"). Harmless on plain Postgres.
    connect_args = {"prepare_threshold": 100} if "psycopg" in url else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = _make_engine(settings.database_url)


def get_session() -> Session:
    with Session(engine) as s:
        yield s


def create_all() -> None:
    """Create every table (dev/test). Production uses Alembic instead."""
    import app.models  # noqa: F401  (register all models on Base)
    SQLModel.metadata.create_all(engine)


def drop_all() -> None:
    import app.models  # noqa: F401
    SQLModel.metadata.drop_all(engine)
