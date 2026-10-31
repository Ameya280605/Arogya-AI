"""Arogya AI - Patient API Schemas.

Module 3, Phase 3.4: Pydantic Request/Response Schemas & Data Contracts.
Defines contracts for research and synthetic patient profiles. Strictly complies
with the zero-PHI governance framework: requires pseudonymous identifiers;
real patient identifiers, names, and contact details are strictly prohibited.
"""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID
from pydantic import AliasChoices, Field
from backend.app.schemas.common import BaseSchema, ORMModel

BiologicalSex = Literal["male", "female", "other", "unknown"]


class PatientBase(BaseSchema):
    """Base schema attributes for patient records.

    Accepts either 'mrn_pseudonym' or 'mrn' as input via AliasChoices,
    ensuring compatibility between API contracts and SQLAlchemy models.
    """

    mrn_pseudonym: str = Field(
        validation_alias=AliasChoices("mrn_pseudonym", "mrn"),
        min_length=3,
        max_length=64,
        description="Pseudonymous subject or synthetic medical record number (e.g. 'SYNTH-PAT-0001')",
        examples=["SYNTH-PAT-0001"],
    )

    @property
    def mrn(self) -> str:
        """Alias property providing convenient access to mrn_pseudonym."""
        return self.mrn_pseudonym
    birth_date: date | None = Field(
        default=None,
        description="Date or synthetic birth reference for demographic stratification",
        examples=["1985-06-15"],
    )
    biological_sex: BiologicalSex | None = Field(
        default=None,
        description="Biological sex classification ('male', 'female', 'other', 'unknown')",
        examples=["female"],
    )
    is_synthetic: bool = Field(
        default=True,
        description="True for artificially generated records; False for licensed public research datasets",
    )


class PatientCreate(PatientBase):
    """Request contract for registering a new research patient record."""

    pass


class PatientUpdate(BaseSchema):
    """Request contract for updating patient profile attributes."""

    birth_date: date | None = Field(
        default=None,
        description="Updated birth date reference",
    )
    biological_sex: BiologicalSex | None = Field(
        default=None,
        description="Updated biological sex classification",
    )
    is_synthetic: bool | None = Field(
        default=None,
        description="Updated synthetic dataset designation",
    )


class PatientResponse(PatientBase, ORMModel):
    """Response contract representing a patient record."""

    id: UUID = Field(
        description="Unique patient identifier",
    )
    created_at: datetime = Field(
        description="Patient record creation timestamp in UTC",
    )
    updated_at: datetime = Field(
        description="Patient record last-modified timestamp in UTC",
    )


class DataQualityIssue(ORMModel):
    """Specific data completeness or consistency finding for a patient record."""

    category: Literal["demographic", "clinical", "unit", "temporal"] = Field(
        description="Category of the quality finding",
    )
    severity: Literal["info", "warning", "critical"] = Field(
        description="Severity level of the finding",
    )
    field: str | None = Field(
        default=None,
        description="Associated domain attribute or clinical measurement code",
    )
    message: str = Field(
        description="Human-readable explanation of the data quality observation",
    )


class DataQualityReport(ORMModel):
    """Holistic data quality and completeness evaluation for a patient."""

    patient_id: UUID = Field(
        description="Evaluated patient identifier",
    )
    completeness_score: int = Field(
        ge=0,
        le=100,
        description="Overall profile completeness percentage (0-100)",
    )
    demographic_score: int = Field(
        ge=0,
        le=100,
        description="Demographic data completeness percentage (0-100)",
    )
    clinical_score: int = Field(
        ge=0,
        le=100,
        description="Clinical encounter and observation completeness percentage (0-100)",
    )
    issues: list[DataQualityIssue] = Field(
        default_factory=list,
        description="List of detected data quality recommendations, warnings, or anomalies",
    )
    has_warnings: bool = Field(
        default=False,
        description="True if any warning or critical quality issues were identified",
    )


class PatientTimelineItem(ORMModel):
    """Unified chronological timeline event across clinical interactions."""

    id: str = Field(
        description="Unique identifier of the underlying event entity",
    )
    event_type: Literal["encounter", "observation", "analysis_run", "audit_event"] = Field(
        description="Domain category of the timeline item",
    )
    title: str = Field(
        description="Display title of the timeline event",
    )
    description: str | None = Field(
        default=None,
        description="Descriptive context or narrative summary",
    )
    timestamp: datetime = Field(
        description="Timestamp of the event in UTC",
    )
    status: str | None = Field(
        default=None,
        description="Lifecycle status or categorical state",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Additional non-sensitive event metadata attributes",
    )


class PatientTimelineResponse(ORMModel):
    """Response envelope for a patient's longitudinal event timeline."""

    patient_id: UUID = Field(
        description="Target patient identifier",
    )
    items: list[PatientTimelineItem] = Field(
        default_factory=list,
        description="Chronological stream of patient interactions, latest first",
    )
    total: int = Field(
        ge=0,
        description="Total number of timeline events",
    )

