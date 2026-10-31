"""Arogya AI — Base Repository.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Provides a foundational class for SQLAlchemy 2.x repositories, standardizing
session handling, parameter validation, and bounded pagination.

TRANSACTION OWNERSHIP POLICY:
Repositories encapsulate query logic and persistence state mutations (adding,
updating, and querying entities). They DO NOT commit or roll back the session.
Transaction boundaries (commit/rollback) belong strictly to the outer caller
(such as the request-scoped session dependency lifecycle get_db_session, a background
job, or an explicit caller with session.begin(): block). Neither repositories
nor domain services commit or roll back transactions independently.
"""

from typing import Generic, TypeVar
from sqlalchemy.orm import Session

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """Base class for all Arogya AI repositories."""

    def __init__(self, session: Session) -> None:
        """Initialize repository with an active SQLAlchemy Session.

        Args:
            session: Active, request-scoped SQLAlchemy Session instance.
        """
        self.session = session

    @staticmethod
    def _sanitize_pagination(
        limit: int = 100,
        offset: int = 0,
        max_limit: int = 500,
    ) -> tuple[int, int]:
        """Validate and clamp pagination parameters to prevent unbounded database queries.

        Args:
            limit: Requested maximum number of records to return.
            offset: Requested starting index offset.
            max_limit: Upper ceiling for query record limits (default 500).

        Returns:
            Tuple of (sanitized_limit, sanitized_offset).
        """
        clamped_limit = max(1, min(limit, max_limit))
        clamped_offset = max(0, offset)
        return clamped_limit, clamped_offset
