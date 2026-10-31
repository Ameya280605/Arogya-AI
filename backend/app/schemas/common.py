"""Arogya AI - Common Schema Utilities & Pagination Contracts.

Provides base Pydantic models for request validation (forbidding unexpected fields)
and response serialization (enabling from_attributes for SQLAlchemy models), along
with generic pagination envelopes and timezone verification.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base model for request payloads.

    Strictly forbids unexpected extra fields to prevent accidental or malicious
    payload pollution.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )


class ORMModel(BaseModel):
    """Base model for response serialization.

    Enables ORM attribute loading (`from_attributes=True`) to seamlessly serialize
    SQLAlchemy model instances.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard generic pagination envelope for collection resources."""

    items: Sequence[T] = Field(
        description="List of records for current page",
    )
    total: int = Field(
        ge=0,
        description="Total number of matching records in collection",
    )
    page: int = Field(
        ge=1,
        default=1,
        description="Current 1-based page number",
    )
    page_size: int = Field(
        ge=1,
        le=100,
        default=20,
        description="Number of records per page",
    )


def ensure_timezone_aware(dt: datetime | None) -> datetime | None:
    """Validate that a datetime instance includes timezone information.

    Args:
        dt: Datetime to inspect.

    Returns:
        The validated datetime with timezone.

    Raises:
        ValueError: If dt is naive (lacks tzinfo).
    """
    if dt is not None and dt.tzinfo is None:
        raise ValueError(
            "Timestamp must be timezone-aware (e.g. UTC ISO 8601 string like '2026-10-25T10:00:00Z')"
        )
    return dt


