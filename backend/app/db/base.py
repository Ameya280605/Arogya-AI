"""Arogya AI - SQLAlchemy Declarative Base.

Defines the declarative base class and exposes its MetaData collection
for future domain entity models (Module 3, Phase 3.3+) and Alembic migrations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models in Arogya AI."""

    pass


# Convenience export for metadata collection used by migrations and schema inspection
metadata = Base.metadata
