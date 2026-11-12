"""Alembic migration environment configuration.

Configures Alembic to use the sync SQLAlchemy engine for migrations
and discovers all models via the Base metadata.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from alembic import context

# Ensure project root is on the path so `app` is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import config and models so metadata is populated
from app.config import settings
from app.database import Base
from app.models import User, Resume, JobDescription, MatchResult  # noqa: F401

# ── Alembic Config ──
config = context.config

# Set the database URL from our app settings (sync driver for migrations)
config.set_main_option("sqlalchemy.url", settings.database_url_sync)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL scripts without connecting to the database.
    """
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
    """Run migrations in 'online' mode with a sync engine.

    Uses psycopg (sync) for migrations — no need for async here.
    """
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
