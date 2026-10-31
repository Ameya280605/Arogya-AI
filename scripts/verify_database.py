#!/usr/bin/env python3
"""Arogya AI — Database Verification Utility.

Module 3, Phase 3.7: Database Verification and Backup Strategy.
Verifies database connectivity, schema completeness, dialect/server versions,
and Alembic migration head alignment without modifying, migrating, or seeding data.

EXIT CODES:
    0 (EXIT_SUCCESS): Connection verified, all domain tables present, Alembic head matched.
    1 (EXIT_CONNECTION_ERROR): Cannot establish or cleanly close a database connection.
    2 (EXIT_SCHEMA_MISSING): Connected, but one or more required domain tables are missing.
    3 (EXIT_MIGRATION_MISMATCH): Tables present, but current Alembic revision != migration head.
    4 (EXIT_CONFIG_ERROR): Invalid settings, malformed URL, or unconfigured database.

SECURITY & SAFETY RULES:
    1. Zero Auto-Mutation: Never executes DDL, migrations, or test inserts.
    2. Credential Protection: Passwords and sensitive query parameters are masked.
    3. Model Parity: Expected tables are derived dynamically from Base.metadata.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import logging
from pathlib import Path
import sys
from typing import Any

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.db.base import Base
import backend.app.db.models  # noqa: F401 - registers all 9 tables in Base.metadata
from backend.app.db.session import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    create_db_engine,
    get_engine,
)
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.verify_database")

# Canonical Exit Codes
EXIT_SUCCESS = 0
EXIT_CONNECTION_ERROR = 1
EXIT_SCHEMA_MISSING = 2
EXIT_MIGRATION_MISMATCH = 3
EXIT_CONFIG_ERROR = 4


@dataclass
class DatabaseVerificationResult:
    """Structured report detailing database connectivity and schema verification."""

    status: str
    exit_code: int
    dialect: str | None = None
    server_version: str | None = None
    target_host: str | None = None
    target_database: str | None = None
    expected_tables: list[str] | None = None
    found_tables: list[str] | None = None
    missing_tables: list[str] | None = None
    current_revision: str | None = None
    expected_revision: str | None = None
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to a sanitized dictionary for reporting."""
        return asdict(self)


def _get_alembic_config(repo_root: Path | None = None) -> Config:
    """Construct an Alembic Config pointing to backend/alembic.ini."""
    root = repo_root or _REPO_ROOT
    ini_path = root / "backend" / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(root / "backend" / "alembic"))
    return cfg


def verify_database(
    *,
    engine: Engine | None = None,
    settings: Settings | None = None,
    repo_root: Path | None = None,
) -> DatabaseVerificationResult:
    """Perform non-destructive database verification and return structured results.

    Args:
        engine: Optional pre-configured SQLAlchemy Engine instance.
        settings: Optional application Settings instance.
        repo_root: Optional repository root path for Alembic discovery.

    Returns:
        DatabaseVerificationResult with status, exit code, and schema diagnostics.
    """
    root = repo_root or _REPO_ROOT
    app_settings = settings or get_settings()

    # 1. Resolve or create target Engine
    target_engine: Engine
    if engine is not None:
        target_engine = engine
    else:
        try:
            target_engine = get_engine(app_settings)
        except (DatabaseConfigurationError, DatabaseConnectionError) as exc:
            return DatabaseVerificationResult(
                status="CONFIG_ERROR",
                exit_code=EXIT_CONFIG_ERROR,
                details=f"Database engine configuration error: {exc}",
            )
        except Exception as exc:
            return DatabaseVerificationResult(
                status="CONFIG_ERROR",
                exit_code=EXIT_CONFIG_ERROR,
                details=f"Unexpected configuration failure: {exc}",
            )

    # 2. Extract safe target metadata (no credentials)
    url = target_engine.url
    target_host = url.host or "localhost" if url.drivername.startswith("postgresql") else "local_file_or_memory"
    target_database = url.database or "default"
    dialect_name = target_engine.dialect.name

    # 3. Verify Connectivity & Retrieve Server Version
    server_version: str | None = None
    try:
        with target_engine.connect() as conn:
            # Query server version safely
            if dialect_name == "postgresql":
                try:
                    ver_result = conn.execute(text("SHOW server_version;")).scalar()
                    server_version = str(ver_result) if ver_result else None
                except Exception:
                    server_version = ".".join(str(x) for x in conn.dialect.server_version_info or ())
            elif dialect_name == "sqlite":
                try:
                    ver_result = conn.execute(text("SELECT sqlite_version();")).scalar()
                    server_version = str(ver_result) if ver_result else None
                except Exception:
                    server_version = "sqlite3"
    except SQLAlchemyError as exc:
        safe_msg = str(exc)
        if url.password:
            safe_msg = safe_msg.replace(url.password, "[REDACTED]")
        return DatabaseVerificationResult(
            status="CONNECTION_ERROR",
            exit_code=EXIT_CONNECTION_ERROR,
            dialect=dialect_name,
            target_host=target_host,
            target_database=target_database,
            details=f"Failed to connect to database: {safe_msg}",
        )
    except Exception as exc:
        return DatabaseVerificationResult(
            status="CONNECTION_ERROR",
            exit_code=EXIT_CONNECTION_ERROR,
            dialect=dialect_name,
            target_host=target_host,
            target_database=target_database,
            details=f"Unexpected connection failure: {exc}",
        )

    # 4. Check Application Schema & Domain Tables
    expected_tables = sorted(list(Base.metadata.tables.keys()))
    try:
        inspector = inspect(target_engine)
        found_tables = sorted(inspector.get_table_names())
    except Exception as exc:
        return DatabaseVerificationResult(
            status="SCHEMA_MISSING",
            exit_code=EXIT_SCHEMA_MISSING,
            dialect=dialect_name,
            server_version=server_version,
            target_host=target_host,
            target_database=target_database,
            expected_tables=expected_tables,
            details=f"Failed to inspect tables: {exc}",
        )

    missing_tables = [tbl for tbl in expected_tables if tbl not in found_tables]
    if missing_tables:
        return DatabaseVerificationResult(
            status="SCHEMA_MISSING",
            exit_code=EXIT_SCHEMA_MISSING,
            dialect=dialect_name,
            server_version=server_version,
            target_host=target_host,
            target_database=target_database,
            expected_tables=expected_tables,
            found_tables=found_tables,
            missing_tables=missing_tables,
            details=f"Missing {len(missing_tables)} required domain table(s): {', '.join(missing_tables)}",
        )

    # 5. Check Alembic Migration Revision Alignment
    current_rev: str | None = None
    expected_head: str | None = None

    try:
        alembic_cfg = _get_alembic_config(root)
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        expected_head = script_dir.get_current_head()

        with target_engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            current_rev = ctx.get_current_revision()
    except Exception as exc:
        return DatabaseVerificationResult(
            status="MIGRATION_MISMATCH",
            exit_code=EXIT_MIGRATION_MISMATCH,
            dialect=dialect_name,
            server_version=server_version,
            target_host=target_host,
            target_database=target_database,
            expected_tables=expected_tables,
            found_tables=found_tables,
            missing_tables=[],
            current_revision=current_rev,
            expected_revision=expected_head,
            details=f"Could not inspect migration state: {exc}",
        )

    if current_rev != expected_head:
        return DatabaseVerificationResult(
            status="MIGRATION_MISMATCH",
            exit_code=EXIT_MIGRATION_MISMATCH,
            dialect=dialect_name,
            server_version=server_version,
            target_host=target_host,
            target_database=target_database,
            expected_tables=expected_tables,
            found_tables=found_tables,
            missing_tables=[],
            current_revision=current_rev,
            expected_revision=expected_head,
            details=(
                f"Alembic revision mismatch: current database revision is '{current_rev}', "
                f"expected migration head is '{expected_head}'."
            ),
        )

    # 6. Verification Succeeded
    return DatabaseVerificationResult(
        status="VERIFIED",
        exit_code=EXIT_SUCCESS,
        dialect=dialect_name,
        server_version=server_version,
        target_host=target_host,
        target_database=target_database,
        expected_tables=expected_tables,
        found_tables=found_tables,
        missing_tables=[],
        current_revision=current_rev,
        expected_revision=expected_head,
        details="Database connection, schema tables, and migration revision verified successfully.",
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for database verification."""
    parser = argparse.ArgumentParser(
        description="Verify Arogya AI database connectivity, schema completeness, and migration revision."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit output formatted as JSON.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress human-readable informational banners.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    result = verify_database()

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif not args.quiet:
        print("=" * 60)
        print("Arogya AI - Database Verification Utility")
        print("=" * 60)
        print(f"Status:            {result.status}")
        print(f"Dialect:           {result.dialect or 'Unknown'}")
        print(f"Server Version:    {result.server_version or 'N/A'}")
        print(f"Target Host:       {result.target_host or 'N/A'}")
        print(f"Target Database:   {result.target_database or 'N/A'}")
        if result.found_tables is not None and result.expected_tables is not None:
            print(f"Domain Tables:     {len(result.found_tables)}/{len(result.expected_tables)} verified")
        if result.missing_tables:
            print(f"Missing Tables:    {', '.join(result.missing_tables)}")
        print(f"Current Revision:  {result.current_revision or 'None'}")
        print(f"Expected Head:     {result.expected_revision or 'None'}")
        print(f"Details:           {result.details}")
        print("=" * 60)
        if result.exit_code == EXIT_SUCCESS:
            print("[OK] Database verification PASSED.")
        else:
            print(f"[FAIL] Database verification FAILED (exit code {result.exit_code}).")

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
