"""Tests for read-only database schema readiness verification."""

from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from backend.app.db import Base
from backend.app.db.session import check_database_schema


def _create_database(revision: str):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
            )
        )
        connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:revision)"),
            {"revision": revision},
        )
    return engine


def test_database_schema_ready_at_current_migration_head():
    engine = _create_database("20261102_access")
    try:
        assert check_database_schema(engine=engine) is True
    finally:
        engine.dispose()


def test_database_schema_not_ready_at_stale_migration_revision():
    engine = _create_database("98574e91500e")
    try:
        assert check_database_schema(engine=engine) is False
    finally:
        engine.dispose()
