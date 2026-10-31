"""Arogya AI - Clinical Observation API Schemas.

Module 3, Phase 3.4: Pydantic Request/Response Schemas & Data Contracts.
Defines contracts for ground-truth clinical measurements (vitals, laboratory findings).
Distinctly represents quantitative vs. qualitative observations and segregates
measurements from probabilistic AI model inferences.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID
from pydantic import Field, field_validator, model_validator
from backend.app.schemas.common import BaseSchema, ORMModel, ensure_timezone_aware


class ObservationBase(BaseSchema):
    """Base schema attributes for clinical observations."""

    code: str = Field(
        min_length=1,
        max_length=64,
        description="Standardized LOINC code or canonical identifier (e.g. '8867-4', 'heart_rate')",
        examples=["8867-4"],
    )
    display_name: str = Field(
        min_length=1,
        max_length=128,
        description="Human-readable concept title (e.g. 'Heart Rate')",
        examples=["Heart Rate"],
    )
    numeric_value: float | None = Field(
        default=None,
        description="Quantitative measurement value (if observation is numeric)",
        examples=[72.0],
    )
    text_value: str | None = Field(
        default=None,
        max_length=255,
        description="Qualitative or categorical finding (if observation is text/status)",
        examples=["regular"],
    )
    unit: str | None = Field(
        default=None,
        max_length=32,
        description="Standard measurement unit (e.g. 'bpm', 'mg/dL', 'degC')",
        examples=["bpm"],
    )
    observed_at: datetime = Field(
        description="Timestamp when measurement was acquired in ISO 8601 UTC",
        examples=["2026-10-25T10:15:00Z"],
    )
    source_metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional device, synthesizer, or methodology metadata; contains no diagnostic labels",
    )

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at_timezone(cls, v: datetime) -> datetime:
        """Enforce timezone awareness on observation timestamp."""
        res = ensure_timezone_aware(v)
        if res is None:
            raise ValueError("observed_at is required and must be timezone-aware")
        return res


class ObservationCreatePayload(ObservationBase):
    """Request contract for recording an observation where encounter context is scoped by the URL path."""

    @model_validator(mode="after")
    def validate_value_presence(self) -> "ObservationCreatePayload":
        """Ensure at least one of numeric_value or text_value is provided."""
        if self.numeric_value is None and self.text_value is None:
            raise ValueError("Observation must provide either 'numeric_value' or 'text_value'")
        return self


class ObservationCreate(ObservationBase):
    """Request contract for recording a clinical observation."""

    encounter_id: UUID = Field(
        description="Identifier of associated encounter",
    )
    patient_id: UUID = Field(
        description="Identifier of associated patient record",
    )

    @model_validator(mode="after")
    def validate_value_presence(self) -> "ObservationCreate":
        """Ensure at least one of numeric_value or text_value is provided."""
        if self.numeric_value is None and self.text_value is None:
            raise ValueError("Observation must provide either 'numeric_value' or 'text_value'")
        return self


class ObservationResponse(ObservationBase, ORMModel):
    """Response contract representing a recorded observation."""

    id: UUID = Field(
        description="Unique observation identifier",
    )
    encounter_id: UUID = Field(
        description="Associated encounter identifier",
    )
    patient_id: UUID = Field(
        description="Associated patient identifier",
    )
    created_at: datetime = Field(
        description="Record persistence timestamp in UTC",
    )

    @field_validator("observed_at", "created_at", mode="before")
    @classmethod
    def ensure_response_tz(cls, v: Any) -> Any:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

