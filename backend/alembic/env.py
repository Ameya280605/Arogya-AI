"""Arogya AI — Alembic Migration Environment.

Module 3, Phase 3.5: Alembic Migrations & Schema Management.
Configures online and offline schema migration execution, binds target metadata
to the shared SQLAlchemy Base, and dynamically resolves database connection URLs
without embedding credentials in version control.
"""

import logging
from logging.config import fileConfig
import os
from pathlib import Path
import sys

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url

# Ensure repository root and backend directory are in sys.path
_current_file = Path(__file__).resolve()
_backend_dir = _current_file.parent.parent
_repo_root = _backend_dir.parent

for _path in (str(_repo_root), str(_backend_dir)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from backend.app.db.base import Base  # noqa: E402
import backend.app.db.models  # noqa: F401, E402 - registers all 9 domain tables in Base.metadata
from backend.app.db.session import normalize_engine_url  # noqa: E402
from backend.app.settings import get_settings  # noqa: E402

# Alembic Config object, which provides access to values within alembic.ini
config = context.config

# Interpret the config file for Python logging if present
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# Shared SQLAlchemy DeclarativeBase metadata
target_metadata = Base.metadata


def mask_url_str(url_str: str) -> str:
    """Safely redact credentials from connection URL strings for logs and error messages."""
    try:
        return make_url(url_str).render_as_string(hide_password=True)
    except Exception:
        return "<redacted-url>"


def get_database_url() -> str:
    """Resolve database connection URL dynamically from settings or CLI overrides.

    Returns:
        Normalized connection string targeting the synchronous Psycopg 3 dialect.

    Raises:
        RuntimeError: If database URL is not configured when running online migrations.
    """
    # 1. Check for command-line override via -x db_url=...
    x_args = context.get_x_argument(as_dictionary=True)
    if "db_url" in x_args and x_args["db_url"]:
        return normalize_engine_url(x_args["db_url"])

    # 2. Check application settings (loads from .env or environment variables)
    settings = get_settings()
    if settings.database_url:
        return normalize_engine_url(settings.database_url)

    # 3. Check alembic.ini main option if set
    config_url = config.get_main_option("sqlalchemy.url")
    if config_url and config_url.strip():
        return normalize_engine_url(config_url.strip())

    # 4. In offline mode, default to postgresql+psycopg:// dialect for DDL generation
    if context.is_offline_mode():
        return "postgresql+psycopg://"

    raise RuntimeError(
        "DATABASE_URL is not configured in settings or environment. "
        "Cannot execute online migrations without a verified database connection."
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL statements directly to stdout or script file without establishing
    a live database connection.
    """
    url = get_database_url()
    masked_url = mask_url_str(url)
    logger.info("Executing offline migration generation for dialect: %s", masked_url)

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Creates an engine and associates a live connection with the migration context.
    """
    url = get_database_url()
    masked_url = mask_url_str(url)
    logger.info("Executing online migrations against target: %s", masked_url)

    connectable = create_engine(
        url,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
