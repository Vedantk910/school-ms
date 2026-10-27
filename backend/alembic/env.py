"""Alembic migration environment.

Wired to the application so that:
- ``target_metadata`` is the app's ``Base.metadata`` (autogenerate sees all 27 tables)
- the database URL comes from ``SCHOOLMS_DATABASE_URL`` (same source as ``app.db``),
  with a fallback to the value in alembic.ini.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importing models registers every table on Base.metadata.
import app.models  # noqa: F401
from app.db import Base
from app.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# When SCHOOLMS_DATABASE_URL is set to a real (non-default) DB, it wins over the
# value in alembic.ini; otherwise the ini URL is used.
db_url = settings.database_url
if db_url and db_url != "sqlite:///./school_ms.db":
    config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
