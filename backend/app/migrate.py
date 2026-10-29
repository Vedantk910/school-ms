"""Bridge between create_all-built databases and Alembic-managed ones.

Databases built via ``create_all`` (dev / first boot / seed) have no
``alembic_version`` table, so the next ``alembic upgrade`` would try to run
the initial migration on top of an already-populated schema. ``ensure_schema``
stamps head in that case, making the DB migration-consistent without touching
data. Databases already under Alembic management are left untouched.
"""
from sqlalchemy import inspect


def ensure_schema(engine) -> None:
    """Stamp ``alembic_version`` to head if the DB was built outside Alembic."""
    insp = inspect(engine)
    if "alembic_version" in insp.get_table_names():
        return  # already managed by migrations

    # Import Alembic lazily: the API function's runtime image may not ship
    # alembic (it's a tooling dep, not a runtime one). A missing module should
    # never take down app startup — only the optional stamp is lost.
    from alembic import command
    from alembic.config import Config

    cfg = Config()
    cfg.set_main_option("script_location", "alembic")
    cfg.set_main_option("sqlalchemy.url", str(engine.url))
    command.stamp(cfg, "head")
