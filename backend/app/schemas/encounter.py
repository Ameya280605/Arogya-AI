"""Arogya AI - Clinical Encounter API Schemas.

Module 3, Phase 3.4: Pydantic Request/Response Schemas & Data Contracts.
Defines contracts for clinical encounter interactions, temporal lifecycle boundaries,
and status tracking.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from backend.app.schemas.common import BaseSchema, ORMModel, ensure_timezone_aware

EncounterType = Literal["ambulatory", "inpatient", "emergency", "synthetic"]
EncounterStatus = Literal["planned", "in_progress", "completed", "cancelled"]


class EncounterBase(BaseSchema):
    """Base schema attributes for clinical encounters."""

    encounter_type: EncounterType = Field(
        default="ambulatory",
        description="Encounter care classification ('ambulatory', 'inpatient', 'emergency', 'synthetic')",
        examples=["ambulatory"],
    )
    status: EncounterStatus = Field(
        default="in_progress",
        description="Lifecycle status ('planned', 'in_progress', 'completed', 'cancelled')",
        examples=["in_progress"],
    )
    start_time: datetime = Field(
        description="Commencement timestamp of encounter in ISO 8601 UTC",
        examples=["2026-10-25T10:00:00Z"],
    )
    end_time: datetime | None = Field(
        default=None,
        description="Conclusion timestamp of encounter in ISO 8601 UTC",
        examples=["2026-10-25T10:45:00Z"],
    )

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timezones(cls, v: datetime | None) -> datetime | None:
        """Enforce timezone awareness on encounter boundary timestamps."""
        return ensure_timezone_aware(v)


class EncounterCreatePayload(EncounterBase):
    """Request contract for creating an encounter where patient_id is scoped by the endpoint path."""

    @model_validator(mode="after")
    def validate_temporal_order(self) -> "EncounterCreatePayload":
        """Verify that conclusion time does not precede commencement time."""
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("end_time cannot be earlier than start_time")
        return self


class EncounterCreate(EncounterBase):
    """Request contract for initiating a clinical encounter."""

    patient_id: UUID = Field(
        description="Foreign key identifier of target patient record",
    )

    @model_validator(mode="after")
    def validate_temporal_order(self) -> "EncounterCreate":
        """Verify that conclusion time does not precede commencement time."""
        if self.end_time is not None and self.end_time < self.start_time:
            raise ValueError("end_time cannot be earlier than start_time")
        return self


class EncounterUpdate(BaseSchema):
    """Request contract for updating an encounter's status or conclusion time."""

    encounter_type: EncounterType | None = Field(
        default=None,
        description="Updated encounter classification",
    )
    status: EncounterStatus | None = Field(
        default=None,
        description="Updated encounter status",
    )
    start_time: datetime | None = Field(
        default=None,
        description="Updated commencement timestamp in UTC",
    )
    end_time: datetime | None = Field(
        default=None,
        description="Updated conclusion timestamp in UTC",
    )

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_timezones(cls, v: datetime | None) -> datetime | None:
        """Enforce timezone awareness on updated timestamps."""
        return ensure_timezone_aware(v)

    @model_validator(mode="after")
    def validate_temporal_order(self) -> "EncounterUpdate":
        """Verify that conclusion time does not precede commencement time if both are provided."""
        if (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time < self.start_time
        ):
            raise ValueError("end_time cannot be earlier than start_time")
        return self


class EncounterResponse(EncounterBase, ORMModel):
    """Response contract representing a clinical encounter."""

    id: UUID = Field(
        description="Unique encounter identifier",
    )
    patient_id: UUID = Field(
        description="Identifier of associated patient record",
    )
    created_at: datetime = Field(
        description="Record creation timestamp in UTC",
    )
    updated_at: datetime = Field(
        description="Record last-modified timestamp in UTC",
    )

    @field_validator("start_time", "end_time", "created_at", "updated_at", mode="before")
    @classmethod
    def ensure_response_tz(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

