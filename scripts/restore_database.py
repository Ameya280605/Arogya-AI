#!/usr/bin/env python3
"""Arogya AI — PostgreSQL Database Restore & Recovery Utility.

Module 3, Phase 3.7: Database Verification and Backup Strategy.
Safely restores a logical custom-format PostgreSQL backup into an explicitly
designated disposable restore-test database and validates schema and migration integrity.

EXIT CODES:
    0 (RESTORE_VERIFIED): Restore completed, domain tables inspected, migration head matched.
    1 (TOOL_MISSING): 'pg_restore' executable not found in PATH or specified location.
    2 (BACKUP_INVALID): Backup file does not exist, is unreadable, or is 0 bytes.
    3 (CONFIG_ERROR): Malformed database configuration or non-PostgreSQL engine URL.
    4 (EXECUTION_ERROR): 'pg_restore' subprocess exited with an error.
    5 (VERIFICATION_FAILED): Restored database is missing required tables or has revision mismatch.
    6 (SAFETY_REFUSED): Refused operation because target database matches application database,
                        contains forbidden keywords (prod/production), or confirmation was missing.

CRITICAL SAFETY RULES:
    1. NEVER Overwrite Application Database: Refuses if target-db == configured application DB.
    2. Explicit Confirmation Required: Requires --confirm-restore-target <exact_target_name>.
    3. Production Guard: Refuses target databases containing 'prod' or 'production'.
    4. Credential Protection: Passwords are NEVER passed in command-line arguments or logged.
    5. Disposable Target Cleanup: Optional cleanup drops ONLY the confirmed restore-test database.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.db.base import Base
import backend.app.db.models  # noqa: F401 - registers all 9 tables in Base.metadata
from backend.app.db.session import normalize_engine_url
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.restore_database")

# Canonical Exit Codes
RESTORE_VERIFIED = 0
TOOL_MISSING = 1
BACKUP_INVALID = 2
CONFIG_ERROR = 3
EXECUTION_ERROR = 4
VERIFICATION_FAILED = 5
SAFETY_REFUSED = 6

FORBIDDEN_TARGET_KEYWORDS = {"prod", "production", "live", "main"}


@dataclass
class RestoreResult:
    """Structured report detailing restore execution and integrity verification."""

    status: str
    exit_code: int
    backup_file: str | None = None
    target_database: str | None = None
    target_host: str | None = None
    verified_tables_count: int = 0
    missing_tables: list[str] | None = None
    restored_revision: str | None = None
    expected_revision: str | None = None
    cleaned_up: bool = False
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to sanitized dictionary."""
        return asdict(self)


def _get_alembic_config(repo_root: Path | None = None) -> Config:
    """Construct an Alembic Config pointing to backend/alembic.ini."""
    root = repo_root or _REPO_ROOT
    ini_path = root / "backend" / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(root / "backend" / "alembic"))
    return cfg


def restore_and_verify_database(
    *,
    backup_file: Path | str,
    target_database: str,
    confirm_restore_target: str,
    settings: Settings | None = None,
    pg_restore_path: str | None = None,
    repo_root: Path | None = None,
    cleanup_target: bool = False,
    confirm_cleanup: str | None = None,
) -> RestoreResult:
    """Execute a safe, isolated database restore into a disposable test target.

    Args:
        backup_file: Path to existing .dump archive file.
        target_database: Explicit disposable database name (must NOT match application DB).
        confirm_restore_target: Confirmation string matching target_database.
        settings: Application Settings containing base database credentials.
        pg_restore_path: Optional explicit path to pg_restore binary.
        repo_root: Optional repository root path.
        cleanup_target: If True, drops the disposable target database after verification.
        confirm_cleanup: Confirmation string matching target_database if cleanup requested.

    Returns:
        RestoreResult with execution status, schema verification, and revision details.
    """
    root = repo_root or _REPO_ROOT
    app_settings = settings or get_settings()

    # 1. Validate Backup File
    dump_path = Path(backup_file).resolve()
    if not dump_path.exists():
        return RestoreResult(
            status="BACKUP_INVALID",
            exit_code=BACKUP_INVALID,
            backup_file=str(dump_path),
            details=f"Backup file '{dump_path}' does not exist.",
        )

    if not dump_path.is_file():
        return RestoreResult(
            status="BACKUP_INVALID",
            exit_code=BACKUP_INVALID,
            backup_file=str(dump_path),
            details=f"Backup path '{dump_path}' is not a regular file.",
        )

    if dump_path.stat().st_size == 0:
        return RestoreResult(
            status="BACKUP_INVALID",
            exit_code=BACKUP_INVALID,
            backup_file=str(dump_path),
            details=f"Backup file '{dump_path}' is 0 bytes (corrupt or empty archive).",
        )

    # 2. Resolve Database Settings & Host/Port/User
    raw_url = app_settings.database_url
    if not raw_url:
        return RestoreResult(
            status="CONFIG_ERROR",
            exit_code=CONFIG_ERROR,
            details="DATABASE_URL is not configured; cannot perform restore.",
        )

    try:
        normalized = normalize_engine_url(raw_url)
        url = make_url(normalized)
    except Exception as exc:
        return RestoreResult(
            status="CONFIG_ERROR",
            exit_code=CONFIG_ERROR,
            details=f"Malformed database URL: {exc}",
        )

    if not url.drivername.startswith("postgresql"):
        return RestoreResult(
            status="CONFIG_ERROR",
            exit_code=CONFIG_ERROR,
            details=(
                f"pg_restore requires a PostgreSQL connection, but database URL dialect "
                f"is '{url.drivername}'."
            ),
        )

    configured_app_db = url.database or "arogya_ai"
    clean_target = target_database.strip()

    # 3. CRITICAL SAFETY GUARDS
    # Guard A: Target must not be empty
    if not clean_target:
        return RestoreResult(
            status="SAFETY_REFUSED",
            exit_code=SAFETY_REFUSED,
            details="Target database name cannot be empty.",
        )

    # Guard B: Confirmation flag must match exact target name
    if confirm_restore_target.strip() != clean_target:
        return RestoreResult(
            status="SAFETY_REFUSED",
            exit_code=SAFETY_REFUSED,
            target_database=clean_target,
            details=(
                f"Confirmation mismatch: --confirm-restore-target '{confirm_restore_target}' "
                f"does not match target database '{clean_target}'."
            ),
        )

    # Guard C: Never restore over the configured application database
    if clean_target.lower() == configured_app_db.lower():
        return RestoreResult(
            status="SAFETY_REFUSED",
            exit_code=SAFETY_REFUSED,
            target_database=clean_target,
            details=(
                f"REFUSING TO RESTORE: Target database '{clean_target}' matches the active "
                f"application database '{configured_app_db}'. Automated restores over the "
                "primary application database are strictly forbidden to prevent accidental data loss."
            ),
        )

    # Guard D: Forbidden keyword check
    target_lower = clean_target.lower()
    if any(kw in target_lower for kw in FORBIDDEN_TARGET_KEYWORDS):
        return RestoreResult(
            status="SAFETY_REFUSED",
            exit_code=SAFETY_REFUSED,
            target_database=clean_target,
            details=(
                f"REFUSING TO RESTORE: Target database '{clean_target}' contains a protected "
                "keyword ('prod', 'production', 'live', or 'main'). Restore tests must target "
                "an explicitly disposable database (e.g. 'arogya_restore_test')."
            ),
        )

    target_host = url.host or "localhost"
    target_port = str(url.port or 5432)
    target_user = url.username or "postgres"
    password = url.password

    # 4. Check pg_restore Executable Availability
    restore_bin = pg_restore_path or shutil.which("pg_restore")
    if not restore_bin or (pg_restore_path and not Path(pg_restore_path).exists() and not shutil.which(pg_restore_path)):
        return RestoreResult(
            status="TOOL_MISSING",
            exit_code=TOOL_MISSING,
            target_host=target_host,
            target_database=clean_target,
            backup_file=str(dump_path),
            details=(
                "PostgreSQL 'pg_restore' utility not found. Ensure PostgreSQL client tools "
                "are installed and added to PATH, or provide --pg-restore-path."
            ),
        )

    # 5. Execute pg_restore into Designated Disposable Database
    # Flags: --clean --if-exists --no-owner --no-privileges
    cmd = [
        str(restore_bin),
        "-h",
        target_host,
        "-p",
        target_port,
        "-U",
        target_user,
        "-d",
        clean_target,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        str(dump_path),
    ]

    sub_env = os.environ.copy()
    if password:
        sub_env["PGPASSWORD"] = password

    try:
        proc = subprocess.run(
            cmd,
            env=sub_env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return RestoreResult(
            status="TOOL_MISSING",
            exit_code=TOOL_MISSING,
            target_host=target_host,
            target_database=clean_target,
            backup_file=str(dump_path),
            details=f"Executable '{restore_bin}' was not found on this system.",
        )
    except Exception as exc:
        return RestoreResult(
            status="EXECUTION_ERROR",
            exit_code=EXECUTION_ERROR,
            target_host=target_host,
            target_database=clean_target,
            backup_file=str(dump_path),
            details=f"Failed to execute pg_restore subprocess: {exc}",
        )

    # Note: pg_restore returns 0 on success, or 1 for minor warnings/ignored errors
    # (e.g. clean on non-existent tables before restore). If returncode > 1, it is a hard error.
    if proc.returncode > 1:
        err_msg = proc.stderr.strip() if proc.stderr else f"Exit code {proc.returncode}"
        if password and password in err_msg:
            err_msg = err_msg.replace(password, "[REDACTED]")
        return RestoreResult(
            status="EXECUTION_ERROR",
            exit_code=EXECUTION_ERROR,
            target_host=target_host,
            target_database=clean_target,
            backup_file=str(dump_path),
            details=f"pg_restore failed with returncode {proc.returncode}: {err_msg}",
        )

    # 6. Verify Restored Schema & Alembic Revision on Disposable Target
    restored_db_url = url.set(database=clean_target).render_as_string(hide_password=False)
    test_engine = create_engine(restored_db_url, pool_pre_ping=True)

    expected_tables = sorted(list(Base.metadata.tables.keys()))
    try:
        inspector = inspect(test_engine)
        found_tables = inspector.get_table_names()
        missing_tables = [t for t in expected_tables if t not in found_tables]

        if missing_tables:
            test_engine.dispose()
            return RestoreResult(
                status="VERIFICATION_FAILED",
                exit_code=VERIFICATION_FAILED,
                target_host=target_host,
                target_database=clean_target,
                backup_file=str(dump_path),
                verified_tables_count=len(found_tables),
                missing_tables=missing_tables,
                details=f"Restored database is missing {len(missing_tables)} domain table(s): {', '.join(missing_tables)}",
            )

        # Inspect Alembic revision
        alembic_cfg = _get_alembic_config(root)
        script_dir = ScriptDirectory.from_config(alembic_cfg)
        expected_head = script_dir.get_current_head()

        with test_engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            restored_rev = ctx.get_current_revision()

        if restored_rev != expected_head:
            test_engine.dispose()
            return RestoreResult(
                status="VERIFICATION_FAILED",
                exit_code=VERIFICATION_FAILED,
                target_host=target_host,
                target_database=clean_target,
                backup_file=str(dump_path),
                verified_tables_count=len(found_tables),
                missing_tables=[],
                restored_revision=restored_rev,
                expected_revision=expected_head,
                details=(
                    f"Restored Alembic revision '{restored_rev}' does not match "
                    f"expected migration head '{expected_head}'."
                ),
            )
    except Exception as exc:
        test_engine.dispose()
        safe_msg = str(exc)
        if password:
            safe_msg = safe_msg.replace(password, "[REDACTED]")
        return RestoreResult(
            status="VERIFICATION_FAILED",
            exit_code=VERIFICATION_FAILED,
            target_host=target_host,
            target_database=clean_target,
            backup_file=str(dump_path),
            details=f"Verification query failed on restored database: {safe_msg}",
        )

    test_engine.dispose()

    # 7. Optional Cleanup of Disposable Target
    cleaned_up = False
    if cleanup_target:
        if confirm_cleanup and confirm_cleanup.strip() == clean_target:
            try:
                maint_url = url.set(database="postgres").render_as_string(hide_password=False)
                maint_engine = create_engine(maint_url, isolation_level="AUTOCOMMIT")
                with maint_engine.connect() as conn:
                    conn.execute(text(f'DROP DATABASE IF EXISTS "{clean_target}";'))
                maint_engine.dispose()
                cleaned_up = True
            except Exception as exc:
                logger.warning(f"Could not automatically drop test database '{clean_target}': {exc}")

    return RestoreResult(
        status="RESTORE_VERIFIED",
        exit_code=RESTORE_VERIFIED,
        target_host=target_host,
        target_database=clean_target,
        backup_file=str(dump_path),
        verified_tables_count=len(expected_tables),
        missing_tables=[],
        restored_revision=restored_rev,
        expected_revision=expected_head,
        cleaned_up=cleaned_up,
        details="Restored database verified successfully: all domain tables and Alembic revision match.",
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for database restore & verification utility."""
    parser = argparse.ArgumentParser(
        description="Safely restore and verify a custom-format PostgreSQL backup in a disposable database."
    )
    parser.add_argument(
        "--backup-file",
        type=str,
        required=True,
        help="Path to the custom-format (.dump) archive file.",
    )
    parser.add_argument(
        "--target-db",
        type=str,
        required=True,
        help="Name of the separate, disposable restore-test database (e.g. arogya_restore_test).",
    )
    parser.add_argument(
        "--confirm-restore-target",
        type=str,
        required=True,
        help="Mandatory exact confirmation of the target database name.",
    )
    parser.add_argument(
        "--pg-restore-path",
        type=str,
        default=None,
        help="Explicit path to pg_restore binary.",
    )
    parser.add_argument(
        "--cleanup-target",
        action="store_true",
        help="Drop the disposable test database after successful verification.",
    )
    parser.add_argument(
        "--confirm-cleanup",
        type=str,
        default=None,
        help="Mandatory confirmation matching target-db if --cleanup-target is passed.",
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

    result = restore_and_verify_database(
        backup_file=args.backup_file,
        target_database=args.target_db,
        confirm_restore_target=args.confirm_restore_target,
        pg_restore_path=args.pg_restore_path,
        cleanup_target=args.cleanup_target,
        confirm_cleanup=args.confirm_cleanup,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif not args.quiet:
        print("=" * 60)
        print("Arogya AI - PostgreSQL Database Restore & Recovery Utility")
        print("=" * 60)
        print(f"Status:            {result.status}")
        print(f"Target Host:       {result.target_host or 'N/A'}")
        print(f"Target Database:   {result.target_database or 'N/A'}")
        print(f"Backup File:       {result.backup_file or 'N/A'}")
        print(f"Tables Verified:   {result.verified_tables_count}")
        print(f"Restored Revision: {result.restored_revision or 'N/A'}")
        print(f"Expected Revision: {result.expected_revision or 'N/A'}")
        print(f"Target Cleaned Up: {result.cleaned_up}")
        print(f"Details:           {result.details}")
        print("=" * 60)
        if result.exit_code == RESTORE_VERIFIED:
            print("[OK] Restore and verification PASSED.")
        else:
            print(f"[FAIL] Restore operation FAILED (exit code {result.exit_code}).")

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
