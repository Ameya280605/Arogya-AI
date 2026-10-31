"""Arogya AI - Database Engine, Session Lifecycle & Connection Handling.

Provides synchronous SQLAlchemy 2.x engine construction, session factories,
FastAPI dependency injection, and lightweight connection verification.
"""

from collections.abc import Generator
import logging
import re
from urllib.parse import urlsplit
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.db")


class DatabaseError(Exception):
    """Base exception for all Arogya AI database errors."""

    pass


class DatabaseConfigurationError(DatabaseError):
    """Raised when database operations are attempted without valid configuration."""

    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connectivity verification fails."""

    pass


# Module-level cached engine and sessionmaker singletons
_cached_engine: Engine | None = None
_cached_engine_url: str | None = None
_cached_session_factory: sessionmaker[Session] | None = None



def normalize_engine_url(url: str) -> str:
    """Normalize database connection URL for synchronous Psycopg 3 execution.

    Args:
        url: Raw connection URL string.

    Returns:
        Normalized URL string targeting the synchronous Psycopg 3 dialect.

    Raises:
        ValueError: If an asynchronous or incompatible driver scheme is specified.
    """
    cleaned = url.strip()
    parsed = urlsplit(cleaned)
    scheme = parsed.scheme.lower()

    if scheme == "postgresql+asyncpg":
        raise ValueError(
            "The configured database_url specifies an asynchronous driver ('postgresql+asyncpg'), "
            "which is incompatible with the synchronous SQLAlchemy engine in Phase 3.2. "
            "Please configure 'postgresql+psycopg://'."
        )

    if scheme == "postgresql+psycopg2":
        raise ValueError(
            "The configured database_url specifies 'postgresql+psycopg2', but the project is "
            "standardized on the modern Psycopg 3 driver. Please configure 'postgresql+psycopg://'."
        )

    # Normalize legacy postgres:// and generic postgresql:// to explicit postgresql+psycopg://
    if scheme == "postgres":
        return re.sub(r"^postgres://", "postgresql+psycopg://", cleaned, flags=re.IGNORECASE)

    if scheme == "postgresql":
        return re.sub(r"^postgresql://", "postgresql+psycopg://", cleaned, flags=re.IGNORECASE)

    return cleaned


def create_db_engine(database_url: str, **kwargs: object) -> Engine:
    """Construct a synchronous SQLAlchemy 2.x Engine.

    Does not establish an immediate network connection upon instantiation (connections
    are acquired lazily on first query execution or pool checkout).

    Args:
        database_url: Connection URI (PostgreSQL or in-memory SQLite for test suites).
        **kwargs: Optional engine keyword overrides.

    Returns:
        Configured SQLAlchemy Engine.

    Raises:
        ValueError: If an unsupported or incompatible URL scheme is provided.
    """
    normalized_url = normalize_engine_url(database_url)
    parsed = urlsplit(normalized_url)

    # Handle isolated in-memory SQLite instances for testing
    if parsed.scheme.lower() == "sqlite":
        engine_kwargs = {
            "connect_args": {"check_same_thread": False},
        }
        # In-memory SQLite requires StaticPool to persist schema across threads/sessions
        if ":memory:" in normalized_url or not parsed.path.lstrip("/"):
            engine_kwargs["poolclass"] = StaticPool
        engine_kwargs.update(kwargs)
        return create_engine(normalized_url, **engine_kwargs)

    # PostgreSQL configuration with robust production pooling defaults
    engine_kwargs: dict[str, object] = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30.0,
        "pool_recycle": 1800,
        "connect_args": {"connect_timeout": 10},
    }
    if "connect_args" in kwargs and isinstance(kwargs["connect_args"], dict):
        merged_connect_args = dict(engine_kwargs["connect_args"])  # type: ignore[arg-type]
        merged_connect_args.update(kwargs.pop("connect_args"))  # type: ignore[arg-type]
        engine_kwargs["connect_args"] = merged_connect_args
    engine_kwargs.update(kwargs)
    return create_engine(normalized_url, **engine_kwargs)


def get_engine(settings: Settings | None = None) -> Engine:
    """Retrieve or construct the application-wide database engine singleton.

    Args:
        settings: Optional Settings instance; uses cached get_settings() if None.

    Returns:
        Active SQLAlchemy Engine.

    Raises:
        DatabaseConfigurationError: If database_url is not configured.
    """
    global _cached_engine, _cached_engine_url
    app_settings = settings or get_settings()

    if not app_settings.database_url:
        raise DatabaseConfigurationError(
            "DATABASE_URL is not configured; cannot initialize database engine."
        )

    normalized = normalize_engine_url(app_settings.database_url)

    # Return cached instance if active and matching URL
    if _cached_engine is not None and _cached_engine_url == normalized:
        return _cached_engine

    # If an engine was previously cached with a different URL, dispose it
    if _cached_engine is not None:
        _cached_engine.dispose()

    _cached_engine = create_db_engine(normalized)
    _cached_engine_url = normalized
    return _cached_engine


def dispose_engine() -> None:
    """Dispose and clear cached engine and session factory singletons.

    Enables clean state reset between isolated test executions.
    """
    global _cached_engine, _cached_engine_url, _cached_session_factory
    if _cached_engine is not None:
        _cached_engine.dispose()
        _cached_engine = None
    _cached_engine_url = None
    _cached_session_factory = None


def get_session_factory(
    engine: Engine | None = None,
    settings: Settings | None = None,
) -> sessionmaker[Session]:
    """Retrieve or construct a SQLAlchemy sessionmaker factory.

    Args:
        engine: Optional Engine instance; if None, uses get_engine(settings).
        settings: Optional Settings instance if engine is not provided.

    Returns:
        Configured sessionmaker callable returning Session instances.
    """
    global _cached_session_factory
    target_engine = engine or get_engine(settings)

    if engine is None and _cached_session_factory is not None:
        return _cached_session_factory

    factory = sessionmaker(
        bind=target_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    if engine is None:
        _cached_session_factory = factory

    return factory


def get_db_session(
    engine: Engine | None = None,
    settings: Settings | None = None,
) -> Generator[Session, None, None]:
    """FastAPI dependency yielding an isolated database session per request.

    Guarantees that transactions are rolled back if an exception occurs
    and sessions are deterministically closed in all execution paths.

    Args:
        engine: Optional Engine instance; if None, uses get_engine(settings).
        settings: Optional Settings instance if engine is not provided.

    Yields:
        Active SQLAlchemy Session.
    """
    factory = get_session_factory(engine=engine, settings=settings)
    session: Session = factory()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI route dependency yielding an isolated request-scoped database session.

    Delegates to get_db_session() using the configured application engine.
    """
    yield from get_db_session()


def check_database_connection(
    engine: Engine | None = None,
    settings: Settings | None = None,
) -> bool:
    """Verify database connectivity using a lightweight query ('SELECT 1').

    Safely acquires a connection, runs the probe query, and releases
    the connection back to the pool without logging credentials.

    Args:
        engine: Optional Engine instance; if None, uses get_engine(settings).
        settings: Optional Settings instance if engine is not provided.

    Returns:
        True if the database is reachable and responds successfully.

    Raises:
        DatabaseConfigurationError: If database_url is not configured.
        DatabaseConnectionError: If connection or query execution fails.
    """
    target_engine = engine or get_engine(settings)

    try:
        with target_engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception as exc:
        logger.warning(
            "Database connectivity probe failed: error_type=%s",
            exc.__class__.__name__,
        )
        raise DatabaseConnectionError(
            f"Database connectivity check failed: {exc.__class__.__name__}"
        ) from exc
