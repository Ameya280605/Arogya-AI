"""Arogya AI - Database Package.

Module 3: Database Persistence & Session Lifecycle.
Provides the SQLAlchemy declarative base, session factory, FastAPI dependency,
connection verification, and clinical domain entity models.
"""

from backend.app.db.base import Base, metadata
from backend.app.db.models import (
    AnalysisRun,
    AuditEvent,
    Encounter,
    Observation,
    Patient,
    Role,
    UploadedAsset,
    User,
    user_roles,
)
from backend.app.db.session import (
    DatabaseConfigurationError,
    DatabaseConnectionError,
    DatabaseError,
    check_database_connection,
    create_db_engine,
    dispose_engine,
    get_db,
    get_db_session,
    get_engine,
    get_session_factory,
    normalize_engine_url,
)

__all__ = [
    "AnalysisRun",
    "AuditEvent",
    "Base",
    "DatabaseConfigurationError",
    "DatabaseConnectionError",
    "DatabaseError",
    "Encounter",
    "Observation",
    "Patient",
    "Role",
    "UploadedAsset",
    "User",
    "check_database_connection",
    "create_db_engine",
    "dispose_engine",
    "get_db",
    "get_db_session",
    "get_engine",
    "get_session_factory",
    "metadata",
    "normalize_engine_url",
    "user_roles",
]
