"""Arogya AI - Database Infrastructure & Session Lifecycle Tests.

Validates SQLAlchemy declarative base, synchronous engine creation,
Psycopg 3 URL normalization, session lifecycle, transaction rollback,
connection verification, and credential protection.
"""

import pytest
from unittest.mock import patch
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.app.db.base import Base, metadata
from backend.app.db.session import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    check_database_connection,
    create_db_engine,
    dispose_engine,
    get_db_session,
    get_engine,
    get_session_factory,
    normalize_engine_url,
)
from backend.app.main import create_app
from backend.app.settings import Settings


@pytest.fixture(autouse=True)
def clean_engine_state():
    """Ensure cached engine and session factory are cleared before and after each test."""
    dispose_engine()
    yield
    dispose_engine()


@pytest.fixture
def sqlite_engine() -> Engine:
    """Provide an isolated in-memory SQLite engine for dialect-independent tests."""
    engine = create_db_engine("sqlite:///:memory:")
    yield engine
    engine.dispose()


@pytest.fixture
def postgres_test_settings() -> Settings:
    """Provide isolated test settings with a valid PostgreSQL URL for lazy engine checks."""
    return Settings(
        app_name="Arogya AI DB Test",
        app_env="testing",
        debug=False,
        database_url="postgresql+psycopg://test_user:test_pass@localhost:5432/arogya_db",
    )


# ---------------------------------------------------------------------------
# Declarative Base & Metadata Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_declarative_base_and_metadata_exports():
    """Verify Declarative Base and MetaData are correctly exported."""
    assert Base is not None
    assert metadata is not None
    assert isinstance(metadata, MetaData)
    assert Base.metadata is metadata
    assert hasattr(metadata, "tables")


# ---------------------------------------------------------------------------
# URL Scheme & Normalization Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_normalize_engine_url_postgres_schemes():
    """Verify legacy postgres:// and generic postgresql:// normalize to postgresql+psycopg://."""
    legacy = "postgres://user:pass@localhost:5432/arogya_db"
    normalized_legacy = normalize_engine_url(legacy)
    assert normalized_legacy.startswith("postgresql+psycopg://")
    assert "user:pass@localhost:5432/arogya_db" in normalized_legacy

    generic = "postgresql://user:pass@localhost:5432/arogya_db"
    normalized_generic = normalize_engine_url(generic)
    assert normalized_generic.startswith("postgresql+psycopg://")
    assert "user:pass@localhost:5432/arogya_db" in normalized_generic

    explicit = "postgresql+psycopg://user:pass@localhost:5432/arogya_db"
    assert normalize_engine_url(explicit) == explicit

    sqlite = "sqlite:///:memory:"
    assert normalize_engine_url(sqlite) == sqlite


@pytest.mark.unit
def test_normalize_engine_url_rejects_incompatible_schemes():
    """Verify incompatible async or legacy drivers fail with clear, descriptive errors."""
    asyncpg_url = "postgresql+asyncpg://user:pass@localhost:5432/arogya_db"
    with pytest.raises(ValueError, match="asynchronous driver.*postgresql\\+asyncpg"):
        normalize_engine_url(asyncpg_url)

    psycopg2_url = "postgresql+psycopg2://user:pass@localhost:5432/arogya_db"
    with pytest.raises(ValueError, match="standardized on the modern Psycopg 3 driver"):
        normalize_engine_url(psycopg2_url)


# ---------------------------------------------------------------------------
# Engine Construction & Laziness Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_engine_fails_when_unconfigured():
    """Verify get_engine raises DatabaseConfigurationError when database_url is absent."""
    empty_settings = Settings(database_url=None)
    with pytest.raises(DatabaseConfigurationError, match="DATABASE_URL is not configured"):
        get_engine(empty_settings)


@pytest.mark.unit
def test_engine_creation_does_not_connect_immediately():
    """Verify create_db_engine does not open a network connection upon instantiation."""
    # Port 54329 is closed; if connection was eager, this would immediately raise an OperationalError
    fake_pg_url = "postgresql+psycopg://test_user:test_pass@127.0.0.1:54329/unreachable_db"
    engine = create_db_engine(fake_pg_url)
    assert isinstance(engine, Engine)
    assert engine.url.port == 54329
    # Engine is constructed without attempting TCP handshake


@pytest.mark.unit
def test_create_app_does_not_connect_to_database(test_settings: Settings):
    """Verify application factory initializes without establishing database connections."""
    app = create_app(test_settings)
    assert app is not None
    from backend.app.db import session as db_session_module

    assert db_session_module._cached_engine is None


@pytest.mark.unit
def test_engine_caching_and_dispose(postgres_test_settings: Settings):
    """Verify get_engine caches engine instances and dispose_engine resets state."""
    engine1 = get_engine(postgres_test_settings)
    engine2 = get_engine(postgres_test_settings)
    assert engine1 is engine2

    dispose_engine()

    engine3 = get_engine(postgres_test_settings)
    assert engine3 is not engine1


# ---------------------------------------------------------------------------
# Session Execution & Lifecycle Tests (In-Memory SQLite)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_session_executes_query_on_test_engine(sqlite_engine: Engine):
    """Verify a SQLAlchemy session executes queries against an in-memory SQLite engine."""
    factory = get_session_factory(engine=sqlite_engine)

    with factory() as session:
        result = session.execute(text("SELECT 42")).scalar()
        assert result == 42


@pytest.mark.unit
def test_session_dependency_lifecycle_success(sqlite_engine: Engine):
    """Verify get_db_session yields an active session and deterministically closes it on exit."""
    session_gen = get_db_session(engine=sqlite_engine)
    session = next(session_gen)

    assert isinstance(session, Session)
    result = session.execute(text("SELECT 100")).scalar()
    assert result == 100

    with patch.object(session, "close", wraps=session.close) as mock_close, patch.object(
        session, "rollback", wraps=session.rollback
    ) as mock_rollback:
        # Completing the generator execution closes the session
        with pytest.raises(StopIteration):
            next(session_gen)

        assert mock_close.call_count == 1
        assert mock_rollback.call_count == 0
        assert not session.in_transaction()
        assert session.get_transaction() is None


@pytest.mark.unit
def test_session_dependency_lifecycle_rollback_on_exception(sqlite_engine: Engine):
    """Verify get_db_session rolls back uncommitted changes and closes upon exception."""
    factory = get_session_factory(engine=sqlite_engine)

    # Create a test table in SQLite
    with factory() as setup_session:
        setup_session.execute(
            text("CREATE TABLE test_records (id INTEGER PRIMARY KEY, name TEXT)")
        )
        setup_session.commit()

    # Attempt to insert within the dependency, then simulate an unhandled exception
    session_gen = get_db_session(engine=sqlite_engine)
    active_session = next(session_gen)

    active_session.execute(
        text("INSERT INTO test_records (id, name) VALUES (1, 'temporary_name')")
    )

    with patch.object(
        active_session, "close", wraps=active_session.close
    ) as mock_close, patch.object(
        active_session, "rollback", wraps=active_session.rollback
    ) as mock_rollback:
        # Throw exception into generator to trigger except block
        with pytest.raises(RuntimeError, match="Simulated route error"):
            session_gen.throw(RuntimeError("Simulated route error"))

        assert mock_rollback.call_count == 1
        assert mock_close.call_count == 1
        assert not active_session.in_transaction()
        assert active_session.get_transaction() is None

    # Verify transaction was rolled back and record was not committed
    with factory() as verify_session:
        count = verify_session.execute(
            text("SELECT COUNT(*) FROM test_records WHERE id = 1")
        ).scalar()
        assert count == 0


# ---------------------------------------------------------------------------
# FastAPI Dependency Injection Test Route
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fastapi_dependency_injection_route(sqlite_engine: Engine):
    """Verify get_db_session works cleanly as a FastAPI route dependency."""
    test_app = FastAPI()

    def get_test_db():
        yield from get_db_session(engine=sqlite_engine)

    @test_app.get("/test-db-query")
    def run_query(db: Session = Depends(get_test_db)):
        val = db.execute(text("SELECT 'connection_alive'")).scalar()
        return {"status": "ok", "value": val}

    client = TestClient(test_app)
    response = client.get("/test-db-query")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "value": "connection_alive"}


# ---------------------------------------------------------------------------
# Connection Verification Probe Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_check_database_connection_success(sqlite_engine: Engine):
    """Verify check_database_connection succeeds with a working engine."""
    assert check_database_connection(engine=sqlite_engine) is True


@pytest.mark.unit
def test_check_database_connection_failure_masks_credentials():
    """Verify check_database_connection fails without leaking connection credentials in error."""
    secret_pass = "SuperSecretDbPassword!123"
    broken_url = f"postgresql+psycopg://app_user:{secret_pass}@127.0.0.1:54329/unreachable_db"
    broken_engine = create_db_engine(broken_url, connect_args={"connect_timeout": 1})

    with pytest.raises(DatabaseConnectionError) as exc_info:
        check_database_connection(engine=broken_engine)

    error_message = str(exc_info.value)
    # Password must not be exposed in the error message
    assert secret_pass not in error_message
    assert "Database connectivity check failed:" in error_message
    # Underlying cause is preserved for internal diagnostics
    assert exc_info.value.__cause__ is not None
