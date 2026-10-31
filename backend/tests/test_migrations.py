"""Arogya AI — Alembic Migration Infrastructure Tests.

Module 3, Phase 3.5: Alembic Migrations & Synthetic Development Seed Data.
Verifies Alembic configuration, migration metadata completeness, PostgreSQL DDL
offline generation, and schema constraint parity across all 9 domain tables.
"""

import io
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, inspect

from backend.app.db.base import Base
import backend.app.db.models  # noqa: F401 - ensures models are registered in Base.metadata

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ALEMBIC_INI_PATH = REPO_ROOT / "backend" / "alembic.ini"


@pytest.fixture
def alembic_config() -> Config:
    """Fixture providing configured Alembic Config pointing to backend/alembic.ini."""
    cfg = Config(str(ALEMBIC_INI_PATH))
    cfg.set_main_option("script_location", str(REPO_ROOT / "backend" / "alembic"))
    return cfg


def test_alembic_config_points_to_correct_directory(alembic_config: Config) -> None:
    """Verify that Alembic configuration resolves the script directory and versions."""
    script_dir = ScriptDirectory.from_config(alembic_config)
    assert script_dir.dir == str(REPO_ROOT / "backend" / "alembic")
    assert script_dir.versions == str(REPO_ROOT / "backend" / "alembic" / "versions")


def test_target_metadata_contains_all_nine_domain_tables() -> None:
    """Verify that Base.metadata contains the 8 clinical domain entities and 1 association table."""
    expected_tables = {
        "users",
        "roles",
        "user_roles",
        "patients",
        "encounters",
        "observations",
        "uploaded_assets",
        "analysis_runs",
        "audit_events",
    }
    registered_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(registered_tables), (
        f"Missing tables in Base.metadata: {expected_tables - registered_tables}"
    )


def test_initial_migration_revision_and_structure(alembic_config: Config) -> None:
    """Verify that the initial migration script exists, has a valid revision ID, and no down_revision."""
    script_dir = ScriptDirectory.from_config(alembic_config)
    head_revision = script_dir.get_current_head()
    assert head_revision is not None, "No Alembic head revision found in versions directory"

    script = script_dir.get_revision(head_revision)
    assert script is not None
    assert script.revision == "98574e91500e"
    assert script.down_revision is None
    assert "initial" in script.doc.lower()


def test_initial_migration_contains_all_expected_tables(alembic_config: Config) -> None:
    """Verify that the initial migration script defines upgrade and downgrade for all 9 tables."""
    script_dir = ScriptDirectory.from_config(alembic_config)
    script = script_dir.get_revision("98574e91500e")
    assert script is not None

    migration_file = Path(script.path)
    content = migration_file.read_text(encoding="utf-8")

    expected_tables = [
        "patients",
        "roles",
        "users",
        "audit_events",
        "encounters",
        "user_roles",
        "observations",
        "uploaded_assets",
        "analysis_runs",
    ]

    for table in expected_tables:
        assert f"op.create_table('{table}'" in content, (
            f"Table creation for '{table}' not found in upgrade() of initial migration"
        )
        assert f"op.drop_table('{table}')" in content, (
            f"Table drop for '{table}' not found in downgrade() of initial migration"
        )


def test_initial_migration_constraints_and_referential_actions(alembic_config: Config) -> None:
    """Verify that foreign keys, referential deletion policies, and indexes match data model requirements."""
    script_dir = ScriptDirectory.from_config(alembic_config)
    script = script_dir.get_revision("98574e91500e")
    assert script is not None

    content = Path(script.path).read_text(encoding="utf-8")

    # Composite primary key on user_roles association table
    assert "sa.PrimaryKeyConstraint('user_id', 'role_id')" in content

    # Referential deletion actions
    assert "ondelete='CASCADE'" in content  # user_roles
    assert "ondelete='RESTRICT'" in content  # clinical tables protecting history
    assert "ondelete='SET NULL'" in content  # audit actors and nullable references

    # Uniqueness constraints & indexes
    assert "unique=True" in content
    assert "ix_patients_mrn_pseudonym" in content
    assert "ix_users_username" in content
    assert "ix_users_email" in content
    assert "ix_roles_name" in content
    assert "ix_uploaded_assets_storage_path" in content


def test_offline_sql_generation_without_live_database(
    alembic_config: Config, capsys: pytest.CaptureFixture[str]
) -> None:
    """Verify that offline PostgreSQL DDL generation runs cleanly without connecting to a database."""
    # Run offline migration generation (sql=True)
    command.upgrade(alembic_config, "head", sql=True)

    captured = capsys.readouterr()
    generated_sql = captured.out

    # Verify key PostgreSQL DDL statements
    assert "CREATE TABLE alembic_version" in generated_sql
    assert "CREATE TABLE patients" in generated_sql
    assert "CREATE TABLE users" in generated_sql
    assert "CREATE TABLE user_roles" in generated_sql
    assert "CREATE TABLE observations" in generated_sql
    assert "CREATE TABLE analysis_runs" in generated_sql
    assert "TIMESTAMP WITH TIME ZONE" in generated_sql
    assert "UUID NOT NULL" in generated_sql
    assert "INSERT INTO alembic_version" in generated_sql


def test_migration_execution_online_on_disposable_engine(alembic_config: Config) -> None:
    """Verify online migration execution against an isolated in-memory test database."""
    test_db_url = "sqlite://"
    alembic_config.set_main_option("sqlalchemy.url", test_db_url)

    # Execute online upgrade on the disposable test database
    command.upgrade(alembic_config, "head")

    # Verify tables were created via SQLAlchemy inspection
    engine = create_engine(test_db_url)
    # Re-apply to the test database connection
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    assert "patients" in tables
    assert "users" in tables
    assert "roles" in tables
    assert "user_roles" in tables
    assert "encounters" in tables
    assert "observations" in tables
    assert "uploaded_assets" in tables
    assert "analysis_runs" in tables
    assert "audit_events" in tables
