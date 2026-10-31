#!/usr/bin/env python3
"""Arogya AI — PostgreSQL Database Backup Utility.

Module 3, Phase 3.7: Database Verification and Backup Strategy.
Creates consistent, non-overwriting, timestamped logical PostgreSQL database backups
using standard 'pg_dump' with custom archive format (-F c) suitable for 'pg_restore'.

EXIT CODES:
    0 (BACKUP_SUCCESS): Backup created, verified non-empty, and written to target path.
    1 (TOOL_MISSING): 'pg_dump' executable was not found in PATH or specified location.
    2 (CONFIG_ERROR): Invalid database configuration or non-PostgreSQL engine URL.
    3 (EXECUTION_ERROR): 'pg_dump' subprocess failed with a nonzero returncode.
    4 (INTEGRITY_ERROR): Dump file missing or 0 bytes after execution.
    5 (DESTINATION_ERROR): Unsafe destination directory or destination file collision.

SECURITY & PRIVACY RULES:
    1. Zero Command-Line Credentials: Passwords are NEVER passed in argv or logged.
    2. Secure Environment: Passwords are provided strictly via PGPASSWORD in subprocess env.
    3. URL Masking: Connection strings are masked in logs and output.
    4. Non-Destructive: Never overwrites existing backups; never deletes older backups.
    5. Artifact Protection: Dumps contain pseudonymized health data and must be protected.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from sqlalchemy.engine import make_url

# Ensure repository root is on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from backend.app.db.session import normalize_engine_url
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.backup_database")

# Canonical Exit Codes
BACKUP_SUCCESS = 0
TOOL_MISSING = 1
CONFIG_ERROR = 2
EXECUTION_ERROR = 3
INTEGRITY_ERROR = 4
DESTINATION_ERROR = 5


@dataclass
class BackupResult:
    """Structured report detailing backup execution outcome."""

    status: str
    exit_code: int
    backup_file: str | None = None
    file_size_bytes: int = 0
    target_host: str | None = None
    target_database: str | None = None
    timestamp_utc: str | None = None
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to sanitized dictionary."""
        return asdict(self)


def generate_backup_filename(timestamp: datetime | None = None) -> str:
    """Generate a standardized timestamped backup filename."""
    ts = timestamp or datetime.now(timezone.utc)
    return f"arogya_ai_backup_{ts.strftime('%Y%m%d_%H%M%S')}.dump"


def create_database_backup(
    *,
    settings: Settings | None = None,
    destination_dir: Path | str | None = None,
    pg_dump_path: str | None = None,
    repo_root: Path | None = None,
    timestamp: datetime | None = None,
) -> BackupResult:
    """Execute a non-destructive PostgreSQL backup using pg_dump.

    Args:
        settings: Application Settings containing database_url.
        destination_dir: Target directory path (default: <repo_root>/backups).
        pg_dump_path: Optional explicit path to pg_dump binary.
        repo_root: Optional repository root path.
        timestamp: Optional explicit datetime for deterministic naming in tests.

    Returns:
        BackupResult containing status, exit code, and file metadata.
    """
    root = repo_root or _REPO_ROOT
    app_settings = settings or get_settings()

    # 1. Resolve & Validate Database Configuration
    raw_url = app_settings.database_url
    if not raw_url:
        return BackupResult(
            status="CONFIG_ERROR",
            exit_code=CONFIG_ERROR,
            details="DATABASE_URL is not configured; cannot perform backup.",
        )

    try:
        normalized = normalize_engine_url(raw_url)
        url = make_url(normalized)
    except Exception as exc:
        return BackupResult(
            status="CONFIG_ERROR",
            exit_code=CONFIG_ERROR,
            details=f"Malformed database URL: {exc}",
        )

    if not url.drivername.startswith("postgresql"):
        return BackupResult(
            status="CONFIG_ERROR",
            exit_code=CONFIG_ERROR,
            details=(
                f"pg_dump requires a PostgreSQL connection, but database URL dialect "
                f"is '{url.drivername}'."
            ),
        )

    target_host = url.host or "localhost"
    target_port = str(url.port or 5432)
    target_user = url.username or "postgres"
    target_db = url.database or "arogya_ai"
    password = url.password

    # 2. Check pg_dump Executable Availability
    dump_bin = pg_dump_path or shutil.which("pg_dump")
    if not dump_bin or (pg_dump_path and not Path(pg_dump_path).exists() and not shutil.which(pg_dump_path)):
        return BackupResult(
            status="TOOL_MISSING",
            exit_code=TOOL_MISSING,
            target_host=target_host,
            target_database=target_db,
            details=(
                "PostgreSQL 'pg_dump' utility not found. Ensure PostgreSQL client tools "
                "are installed and added to PATH, or provide --pg-dump-path."
            ),
        )

    # 3. Resolve Destination Directory & Target File
    dest_path = Path(destination_dir) if destination_dir else (root / "backups")
    try:
        dest_path.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        return BackupResult(
            status="DESTINATION_ERROR",
            exit_code=DESTINATION_ERROR,
            details=f"Cannot create destination directory '{dest_path}': {exc}",
        )

    filename = generate_backup_filename(timestamp)
    target_file = dest_path / filename

    if target_file.exists():
        return BackupResult(
            status="DESTINATION_ERROR",
            exit_code=DESTINATION_ERROR,
            target_host=target_host,
            target_database=target_db,
            details=f"Destination backup file '{target_file}' already exists; refusing to overwrite.",
        )

    # 4. Construct Command (Custom format -F c, blobs included, verbose)
    cmd = [
        str(dump_bin),
        "-h",
        target_host,
        "-p",
        target_port,
        "-U",
        target_user,
        "-d",
        target_db,
        "-F",
        "c",
        "-b",
        "-f",
        str(target_file),
    ]

    # 5. Execute Subprocess with Safe Credential Environment
    sub_env = os.environ.copy()
    if password:
        sub_env["PGPASSWORD"] = password

    now_utc = (timestamp or datetime.now(timezone.utc)).isoformat()
    try:
        proc = subprocess.run(
            cmd,
            env=sub_env,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        if target_file.exists():
            target_file.unlink(missing_ok=True)
        return BackupResult(
            status="TOOL_MISSING",
            exit_code=TOOL_MISSING,
            target_host=target_host,
            target_database=target_db,
            details=f"Executable '{dump_bin}' was not found on this system.",
        )
    except Exception as exc:
        if target_file.exists():
            target_file.unlink(missing_ok=True)
        return BackupResult(
            status="EXECUTION_ERROR",
            exit_code=EXECUTION_ERROR,
            target_host=target_host,
            target_database=target_db,
            details=f"Failed to execute pg_dump subprocess: {exc}",
        )

    if proc.returncode != 0:
        if target_file.exists():
            target_file.unlink(missing_ok=True)
        err_msg = proc.stderr.strip() if proc.stderr else f"Exit code {proc.returncode}"
        if password and password in err_msg:
            err_msg = err_msg.replace(password, "[REDACTED]")
        return BackupResult(
            status="EXECUTION_ERROR",
            exit_code=EXECUTION_ERROR,
            target_host=target_host,
            target_database=target_db,
            details=f"pg_dump execution failed: {err_msg}",
        )

    # 6. Verify Backup File Existence and Non-Empty Size
    if not target_file.exists():
        return BackupResult(
            status="INTEGRITY_ERROR",
            exit_code=INTEGRITY_ERROR,
            target_host=target_host,
            target_database=target_db,
            details=f"Expected backup file '{target_file}' was not created.",
        )

    file_size = target_file.stat().st_size
    if file_size == 0:
        target_file.unlink(missing_ok=True)
        return BackupResult(
            status="INTEGRITY_ERROR",
            exit_code=INTEGRITY_ERROR,
            target_host=target_host,
            target_database=target_db,
            details="Backup completed with 0 bytes (empty archive); removed corrupt artifact.",
        )

    return BackupResult(
        status="BACKUP_SUCCESS",
        exit_code=BACKUP_SUCCESS,
        backup_file=str(target_file),
        file_size_bytes=file_size,
        target_host=target_host,
        target_database=target_db,
        timestamp_utc=now_utc,
        details="PostgreSQL logical custom-format backup created and verified successfully.",
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for database backup utility."""
    parser = argparse.ArgumentParser(
        description="Create a logical custom-format PostgreSQL backup of the Arogya AI database."
    )
    parser.add_argument(
        "--destination",
        type=str,
        default=None,
        help="Target directory for backup file (default: <repo_root>/backups).",
    )
    parser.add_argument(
        "--pg-dump-path",
        type=str,
        default=None,
        help="Explicit path to pg_dump executable.",
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

    result = create_database_backup(
        destination_dir=args.destination,
        pg_dump_path=args.pg_dump_path,
    )

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    elif not args.quiet:
        print("=" * 60)
        print("Arogya AI - PostgreSQL Database Backup Utility")
        print("=" * 60)
        print(f"Status:            {result.status}")
        print(f"Target Host:       {result.target_host or 'N/A'}")
        print(f"Target Database:   {result.target_database or 'N/A'}")
        if result.backup_file:
            print(f"Backup File:       {result.backup_file}")
            print(f"File Size:         {result.file_size_bytes:,} bytes")
        print(f"Timestamp (UTC):   {result.timestamp_utc or 'N/A'}")
        print(f"Details:           {result.details}")
        print("=" * 60)
        if result.exit_code == BACKUP_SUCCESS:
            print("[OK] Backup creation PASSED.")
            print("Notice: A successful pg_dump exit code verifies archive creation,")
            print("not full logical restore validity. Test restores periodically.")
        else:
            print(f"[FAIL] Backup creation FAILED (exit code {result.exit_code}).")

    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
