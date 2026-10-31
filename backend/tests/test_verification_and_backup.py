"""Arogya AI — Database Verification & Backup Strategy Tests.

Module 3, Phase 3.7: Database Verification and Backup Strategy.
Verifies database verification utility, schema completeness, Alembic revision alignment,
backup command execution, secret redaction, non-overwriting timestamped filenames,
corrupt archive detection, and restore safety guards against production/application databases.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
import backend.app.db.models  # noqa: F401 - registers all 9 tables in Base.metadata
from backend.app.settings import Settings
from scripts.backup_database import (
    BACKUP_SUCCESS,
    CONFIG_ERROR as BACKUP_CONFIG_ERROR,
    DESTINATION_ERROR,
    EXECUTION_ERROR as BACKUP_EXECUTION_ERROR,
    INTEGRITY_ERROR,
    TOOL_MISSING as BACKUP_TOOL_MISSING,
    create_database_backup,
    generate_backup_filename,
)
from scripts.restore_database import (
    BACKUP_INVALID,
    CONFIG_ERROR as RESTORE_CONFIG_ERROR,
    EXECUTION_ERROR as RESTORE_EXECUTION_ERROR,
    RESTORE_VERIFIED,
    SAFETY_REFUSED,
    TOOL_MISSING as RESTORE_TOOL_MISSING,
    VERIFICATION_FAILED,
    restore_and_verify_database,
)
from scripts.verify_database import (
    EXIT_CONFIG_ERROR,
    EXIT_CONNECTION_ERROR,
    EXIT_MIGRATION_MISMATCH,
    EXIT_SCHEMA_MISSING,
    EXIT_SUCCESS,
    verify_database,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


# -----------------------------------------------------------------------------
# Database Verification Utility Tests
# -----------------------------------------------------------------------------

def test_verify_database_success() -> None:
    """Verify that a fully migrated database with all 9 tables and Alembic head returns EXIT_SUCCESS."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Create all domain tables
    Base.metadata.create_all(engine)

    # Create alembic_version table with matching head revision
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('98574e91500e');"))

    result = verify_database(engine=engine, repo_root=REPO_ROOT)
    assert result.exit_code == EXIT_SUCCESS
    assert result.status == "VERIFIED"
    assert result.dialect == "sqlite"
    assert result.missing_tables == []
    assert result.current_revision == "98574e91500e"
    assert result.expected_revision == "98574e91500e"
    assert len(result.found_tables or []) >= 9


def test_verify_database_missing_schema() -> None:
    """Verify that an empty database without tables returns EXIT_SCHEMA_MISSING."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    result = verify_database(engine=engine, repo_root=REPO_ROOT)
    assert result.exit_code == EXIT_SCHEMA_MISSING
    assert result.status == "SCHEMA_MISSING"
    assert len(result.missing_tables or []) == 9
    assert "users" in (result.missing_tables or [])
    assert "patients" in (result.missing_tables or [])


def test_verify_database_migration_mismatch() -> None:
    """Verify that a database with outdated Alembic revision returns EXIT_MIGRATION_MISMATCH."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    # Simulate outdated migration revision
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY);"))
        conn.execute(text("INSERT INTO alembic_version (version_num) VALUES ('outdated_rev_0001');"))

    result = verify_database(engine=engine, repo_root=REPO_ROOT)
    assert result.exit_code == EXIT_MIGRATION_MISMATCH
    assert result.status == "MIGRATION_MISMATCH"
    assert result.current_revision == "outdated_rev_0001"
    assert result.expected_revision == "98574e91500e"


def test_verify_database_connection_failure_and_secret_redaction() -> None:
    """Verify that connection failure returns EXIT_CONNECTION_ERROR and masks password."""
    secret_pw = "SuperSecretPassword123!"
    bad_url = f"postgresql+psycopg://arogya_user:{secret_pw}@127.0.0.1:54399/nonexistent_arogya_db"
    settings = Settings(database_url=bad_url)

    result = verify_database(settings=settings, repo_root=REPO_ROOT)
    assert result.exit_code == EXIT_CONNECTION_ERROR
    assert result.status == "CONNECTION_ERROR"
    # Never leaks the raw secret password in details
    assert secret_pw not in (result.details or "")

    # Test explicit redaction when an exception string contains the password
    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"
    mock_engine.url.host = "localhost"
    mock_engine.url.database = "mock_db"
    mock_engine.url.drivername = "postgresql+psycopg"
    mock_engine.url.password = "SensitivePass789!"
    from sqlalchemy.exc import OperationalError
    mock_engine.connect.side_effect = OperationalError(
        "FATAL: password authentication failed for user 'SensitivePass789!'",
        None,
        None,
    )
    res_mock = verify_database(engine=mock_engine, repo_root=REPO_ROOT)
    assert res_mock.exit_code == EXIT_CONNECTION_ERROR
    assert "SensitivePass789!" not in (res_mock.details or "")
    assert "[REDACTED]" in (res_mock.details or "")


# -----------------------------------------------------------------------------
# PostgreSQL Backup Utility Tests
# -----------------------------------------------------------------------------

def test_backup_tool_missing_pg_dump(tmp_path: Path) -> None:
    """Verify that a missing pg_dump executable returns TOOL_MISSING exit code."""
    settings = Settings(database_url="postgresql+psycopg://user:pw@localhost:5432/arogya_ai")
    result = create_database_backup(
        settings=settings,
        destination_dir=tmp_path,
        pg_dump_path=str(tmp_path / "nonexistent_pg_dump.exe"),
    )
    assert result.exit_code == BACKUP_TOOL_MISSING
    assert result.status == "TOOL_MISSING"
    assert "pg_dump" in (result.details or "")


def test_backup_refuses_non_postgres_dialect(tmp_path: Path) -> None:
    """Verify that running backup against SQLite or invalid dialect returns CONFIG_ERROR."""
    settings = Settings.model_construct(database_url="sqlite:///test.db")
    result = create_database_backup(
        settings=settings,
        destination_dir=tmp_path,
    )
    assert result.exit_code == BACKUP_CONFIG_ERROR
    assert result.status == "CONFIG_ERROR"
    assert "PostgreSQL" in (result.details or "")


def test_backup_timestamp_and_non_overwriting(tmp_path: Path) -> None:
    """Verify timestamped backup file creation and refusal to overwrite existing backups."""
    settings = Settings(database_url="postgresql+psycopg://user:pw@localhost:5432/arogya_ai")
    fake_pg_dump = tmp_path / "mock_pg_dump.exe"
    fake_pg_dump.write_text("mock")

    fixed_time = datetime(2026, 10, 25, 12, 0, 0, tzinfo=timezone.utc)
    expected_filename = generate_backup_filename(fixed_time)

    # 1. Mock subprocess to simulate pg_dump successfully creating a non-empty dump
    def mock_subprocess_run(cmd, **kwargs):
        # cmd[-1] is output file path
        out_file = Path(cmd[-1])
        out_file.write_bytes(b"PGDMP\x01\x02\x03FAKE_CUSTOM_FORMAT_ARCHIVE")
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = ""
        return mock_proc

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        result1 = create_database_backup(
            settings=settings,
            destination_dir=tmp_path,
            pg_dump_path=str(fake_pg_dump),
            timestamp=fixed_time,
        )

    assert result1.exit_code == BACKUP_SUCCESS
    assert result1.backup_file is not None
    assert Path(result1.backup_file).name == expected_filename
    assert result1.file_size_bytes > 0
    assert Path(result1.backup_file).exists()

    # 2. Attempting to create the same timestamped backup again MUST refuse overwrite
    result2 = create_database_backup(
        settings=settings,
        destination_dir=tmp_path,
        pg_dump_path=str(fake_pg_dump),
        timestamp=fixed_time,
    )
    assert result2.exit_code == DESTINATION_ERROR
    assert result2.status == "DESTINATION_ERROR"
    assert "already exists" in (result2.details or "")


def test_backup_command_failure_and_partial_cleanup(tmp_path: Path) -> None:
    """Verify that pg_dump failure returns EXECUTION_ERROR and cleans up partial artifact."""
    settings = Settings(database_url="postgresql+psycopg://user:SecretPassword123!@localhost:5432/arogya_ai")
    fake_pg_dump = tmp_path / "mock_pg_dump.exe"
    fake_pg_dump.write_text("mock")

    def mock_failing_run(cmd, **kwargs):
        # Create a partial file before failure
        out_file = Path(cmd[-1])
        out_file.write_text("partial corrupted content")
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = "pg_dump: error: connection failed: password SecretPassword123! rejected"
        return mock_proc

    with patch("subprocess.run", side_effect=mock_failing_run):
        result = create_database_backup(
            settings=settings,
            destination_dir=tmp_path,
            pg_dump_path=str(fake_pg_dump),
        )

    assert result.exit_code == BACKUP_EXECUTION_ERROR
    assert result.status == "EXECUTION_ERROR"
    # Ensure password was masked
    assert "SecretPassword123!" not in (result.details or "")
    assert "[REDACTED]" in (result.details or "")
    # Ensure partial file was removed
    dump_files = list(tmp_path.glob("*.dump"))
    assert len(dump_files) == 0


def test_backup_empty_file_detection(tmp_path: Path) -> None:
    """Verify that a 0-byte dump is detected as corrupt, removed, and returns INTEGRITY_ERROR."""
    settings = Settings(database_url="postgresql+psycopg://user:pw@localhost:5432/arogya_ai")
    fake_pg_dump = tmp_path / "mock_pg_dump.exe"
    fake_pg_dump.write_text("mock")

    def mock_empty_run(cmd, **kwargs):
        # Create empty 0-byte file
        out_file = Path(cmd[-1])
        out_file.touch()
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stderr = ""
        return mock_proc

    with patch("subprocess.run", side_effect=mock_empty_run):
        result = create_database_backup(
            settings=settings,
            destination_dir=tmp_path,
            pg_dump_path=str(fake_pg_dump),
        )

    assert result.exit_code == INTEGRITY_ERROR
    assert result.status == "INTEGRITY_ERROR"
    assert "0 bytes" in (result.details or "")
    assert len(list(tmp_path.glob("*.dump"))) == 0


# -----------------------------------------------------------------------------
# PostgreSQL Restore & Recovery Safety Tests
# -----------------------------------------------------------------------------

def test_restore_refusal_when_target_matches_application_database(tmp_path: Path) -> None:
    """CRITICAL SAFETY TEST: Refuse restore when target-db matches configured application database."""
    app_db = "arogya_primary_db"
    settings = Settings(database_url=f"postgresql+psycopg://user:pw@localhost:5432/{app_db}")

    backup_file = tmp_path / "test.dump"
    backup_file.write_bytes(b"PGDMP_DUMMY_DATA")

    result = restore_and_verify_database(
        backup_file=backup_file,
        target_database=app_db,
        confirm_restore_target=app_db,
        settings=settings,
    )
    assert result.exit_code == SAFETY_REFUSED
    assert result.status == "SAFETY_REFUSED"
    assert "REFUSING TO RESTORE" in (result.details or "")
    assert "matches the active application database" in (result.details or "")


def test_restore_refusal_without_matching_confirmation(tmp_path: Path) -> None:
    """Verify restore refuses execution if confirmation string does not match target database."""
    settings = Settings(database_url="postgresql+psycopg://user:pw@localhost:5432/arogya_app")

    backup_file = tmp_path / "test.dump"
    backup_file.write_bytes(b"PGDMP_DUMMY_DATA")

    result = restore_and_verify_database(
        backup_file=backup_file,
        target_database="arogya_restore_test",
        confirm_restore_target="wrong_confirmation_name",
        settings=settings,
    )
    assert result.exit_code == SAFETY_REFUSED
    assert result.status == "SAFETY_REFUSED"
    assert "Confirmation mismatch" in (result.details or "")


def test_restore_refusal_on_forbidden_keywords(tmp_path: Path) -> None:
    """Verify restore refuses target database names containing 'prod', 'production', or 'live'."""
    settings = Settings(database_url="postgresql+psycopg://user:pw@localhost:5432/arogya_dev")

    backup_file = tmp_path / "test.dump"
    backup_file.write_bytes(b"PGDMP_DUMMY_DATA")

    for forbidden_target in ["arogya_prod_restore", "production_db", "live_clinical"]:
        result = restore_and_verify_database(
            backup_file=backup_file,
            target_database=forbidden_target,
            confirm_restore_target=forbidden_target,
            settings=settings,
        )
        assert result.exit_code == SAFETY_REFUSED
        assert "protected keyword" in (result.details or "")


def test_restore_backup_file_validation(tmp_path: Path) -> None:
    """Verify that missing, directory, or 0-byte backup files return BACKUP_INVALID."""
    settings = Settings(database_url="postgresql+psycopg://user:pw@localhost:5432/arogya_dev")

    # 1. Nonexistent file
    res1 = restore_and_verify_database(
        backup_file=tmp_path / "missing.dump",
        target_database="arogya_restore_test",
        confirm_restore_target="arogya_restore_test",
        settings=settings,
    )
    assert res1.exit_code == BACKUP_INVALID

    # 2. Empty 0-byte file
    empty_file = tmp_path / "empty.dump"
    empty_file.touch()
    res2 = restore_and_verify_database(
        backup_file=empty_file,
        target_database="arogya_restore_test",
        confirm_restore_target="arogya_restore_test",
        settings=settings,
    )
    assert res2.exit_code == BACKUP_INVALID
    assert "0 bytes" in (res2.details or "")


def test_restore_missing_pg_restore(tmp_path: Path) -> None:
    """Verify that a missing pg_restore executable returns TOOL_MISSING exit code."""
    settings = Settings(database_url="postgresql+psycopg://user:pw@localhost:5432/arogya_dev")
    backup_file = tmp_path / "valid.dump"
    backup_file.write_bytes(b"PGDMP_DATA")

    res = restore_and_verify_database(
        backup_file=backup_file,
        target_database="arogya_restore_test",
        confirm_restore_target="arogya_restore_test",
        settings=settings,
        pg_restore_path=str(tmp_path / "missing_pg_restore.exe"),
    )
    assert res.exit_code == RESTORE_TOOL_MISSING
    assert "pg_restore" in (res.details or "")
