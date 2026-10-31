"""Arogya AI - Overview Dashboard API Schemas & Data Contracts.

Module 5, Phase 5.1: Dashboard Data Contracts.
Defines strongly-typed, validated Pydantic response contracts for the Overview Dashboard:
- Patient and encounter cohort summaries.
- Analysis-run totals and execution status breakdowns.
- Pending clinical review queue metrics and candidate item previews.
- Sanitized recent system activity telemetry.
- Composed DashboardOverviewResponse aggregating all sections.

Governance & Safety Tenets:
- Counts use non-negative integer constraints (ge=0).
- All timestamps must be timezone-aware UTC datetime objects.
- Summaries strictly exclude PHI, client credentials, and raw diagnostic conclusions.
- Status names match existing SQLAlchemy models and Alembic schemas without speculative additions.
- Valid zero counts, empty lists, and unavailable optional metadata are clearly distinguished.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import Field, field_validator, model_validator

from backend.app.schemas.common import BaseSchema, PaginatedResponse, ensure_timezone_aware

AnalysisRunStatus = Literal["queued", "running", "completed", "failed", "abstained"]


# ---------------------------------------------------------------------------
# Section A: Patient and Encounter Summaries
# ---------------------------------------------------------------------------


class PatientSummary(BaseSchema):
    """Aggregate patient cohort metrics for the overview dashboard."""

    total_patients: int = Field(
        ge=0,
        description="Total registered patient profiles across synthetic and research cohorts",
    )
    synthetic_patients: int = Field(
        ge=0,
        description="Count of artificially generated synthetic patient profiles",
    )
    research_cohort_patients: int = Field(
        ge=0,
        description="Count of licensed/de-identified research dataset patient profiles",
    )
    generated_at: datetime = Field(
        description="Timestamp in UTC when patient cohort counts were computed",
    )

    @field_validator("generated_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_cohort_counts(self) -> "PatientSummary":
        if self.total_patients != (self.synthetic_patients + self.research_cohort_patients):
            raise ValueError(
                f"total_patients ({self.total_patients}) must equal the sum of synthetic_patients "
                f"({self.synthetic_patients}) and research_cohort_patients ({self.research_cohort_patients})"
            )
        return self


class EncounterSummary(BaseSchema):
    """Aggregate clinical encounter metrics for the overview dashboard."""

    total_encounters: int = Field(
        ge=0,
        description="Total recorded clinical encounters across all statuses",
    )
    planned: int = Field(
        default=0,
        ge=0,
        description="Count of encounters scheduled or planned",
    )
    in_progress: int = Field(
        default=0,
        ge=0,
        description="Count of encounters currently active or underway",
    )
    completed: int = Field(
        default=0,
        ge=0,
        description="Count of successfully concluded encounters",
    )
    cancelled: int = Field(
        default=0,
        ge=0,
        description="Count of cancelled or aborted encounters",
    )
    reporting_period_start: datetime | None = Field(
        default=None,
        description="Optional commencement timestamp of encounter aggregation window in UTC",
    )
    reporting_period_end: datetime | None = Field(
        default=None,
        description="Optional conclusion timestamp of encounter aggregation window in UTC",
    )
    generated_at: datetime = Field(
        description="Timestamp in UTC when encounter counts were computed",
    )

    @field_validator("reporting_period_start", "reporting_period_end", "generated_at")
    @classmethod
    def validate_tz(cls, v: datetime | None) -> datetime | None:
        return ensure_timezone_aware(v)

    @model_validator(mode="after")
    def validate_encounter_counts(self) -> "EncounterSummary":
        status_sum = self.planned + self.in_progress + self.completed + self.cancelled
        if self.total_encounters != status_sum:
            raise ValueError(
                f"total_encounters ({self.total_encounters}) must equal sum of status counts ({status_sum})"
            )
        if (
            self.reporting_period_start is not None
            and self.reporting_period_end is not None
            and self.reporting_period_end < self.reporting_period_start
        ):
            raise ValueError("reporting_period_end cannot precede reporting_period_start")
        return self


# ---------------------------------------------------------------------------
# Section B: Analysis Summary
# ---------------------------------------------------------------------------


class AnalysisStatusBreakdown(BaseSchema):
    """Status distribution breakdown for AI model analysis executions."""

    queued: int = Field(
        default=0,
        ge=0,
        description="Analysis runs queued awaiting compute worker dispatch",
    )
    running: int = Field(
        default=0,
        ge=0,
        description="Analysis runs actively executing inference pipelines",
    )
    completed: int = Field(
        default=0,
        ge=0,
        description="Analysis runs successfully completed with research findings",
    )
    failed: int = Field(
        default=0,
        ge=0,
        description="Analysis runs terminated abnormally due to runtime errors",
    )
    abstained: int = Field(
        default=0,
        ge=0,
        description="Analysis runs abstained due to high entropy, uncertainty, or safety filters",
    )


class AnalysisSummary(BaseSchema):
    """Aggregate analysis run metrics for the overview dashboard."""

    total_runs: int = Field(
        ge=0,
        description="Total analysis runs recorded across all execution states",
    )
    by_status: AnalysisStatusBreakdown = Field(
        description="Detailed execution status breakdown",
    )
    active_models_observed: list[str] = Field(
        default_factory=list,
        description="List of distinct model identifiers observed in the current analysis registry",
    )
    generated_at: datetime = Field(
        description="Timestamp in UTC when analysis metrics were generated",
    )

    @field_validator("generated_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_totals(self) -> "AnalysisSummary":
        status_sum = (
            self.by_status.queued
            + self.by_status.running
            + self.by_status.completed
            + self.by_status.failed
            + self.by_status.abstained
        )
        if self.total_runs != status_sum:
            raise ValueError(
                f"total_runs ({self.total_runs}) must equal sum of status counts ({status_sum})"
            )
        return self


# ---------------------------------------------------------------------------
# Section C: Pending Review Queue
# ---------------------------------------------------------------------------


class PendingReviewItem(BaseSchema):
    """Representation of an analysis run or finding candidate awaiting clinical review."""

    run_id: UUID = Field(
        description="Analysis run UUID identifying the evaluated output",
    )
    patient_id: UUID = Field(
        description="Patient UUID associated with the pending analysis",
    )
    encounter_id: UUID | None = Field(
        default=None,
        description="Optional encounter UUID context",
    )
    model_name: str = Field(
        description="Canonical identifier of the model that produced findings",
    )
    model_version: str = Field(
        description="Version of the model that executed the analysis",
    )
    status: str = Field(
        description="Analysis lifecycle state (e.g. 'completed' or 'abstained')",
    )
    abstained: bool = Field(
        default=False,
        description="True if model abstained due to safety checks or high uncertainty",
    )
    created_at: datetime = Field(
        description="Timestamp when the analysis run was created in UTC",
    )

    @field_validator("created_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)  # type: ignore[return-value]


class PendingReviewQueueSummary(BaseSchema):
    """Pending clinical review queue metrics and preview for the overview dashboard."""

    pending_count: int = Field(
        ge=0,
        description="Total number of completed or abstained analysis runs awaiting clinician review",
    )
    items: list[PendingReviewItem] = Field(
        default_factory=list,
        description="Preview of pending review items bounded for overview presentation",
    )
    generated_at: datetime = Field(
        description="Timestamp in UTC when review queue was summarized",
    )

    @field_validator("generated_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)  # type: ignore[return-value]


class PendingReviewQueuePaginated(PaginatedResponse[PendingReviewItem]):
    """Paginated collection of pending review items for review queue endpoints."""

    pass


# ---------------------------------------------------------------------------
# Section D: Recent System Activity
# ---------------------------------------------------------------------------


class RecentActivityItem(BaseSchema):
    """Sanitized, non-PHI summary of a recent system or research event."""

    id: UUID = Field(
        description="Unique identifier of the audit event or activity record",
    )
    event_type: str = Field(
        description="Classification of event (e.g. 'analysis.started', 'user.login', 'case.created')",
    )
    action: str = Field(
        description="Action category ('create', 'read', 'update', 'delete', 'execute')",
    )
    resource_type: str | None = Field(
        default=None,
        description="Target resource category ('patient', 'encounter', 'asset', 'analysis_run')",
    )
    resource_id: str | None = Field(
        default=None,
        description="Identifier of target resource (e.g. UUID string or pseudonym)",
    )
    description: str | None = Field(
        default=None,
        description="Safe, human-readable event summary omitting sensitive clinical or credential data",
    )
    timestamp: datetime = Field(
        description="Event recording timestamp in UTC",
    )

    @field_validator("timestamp")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)  # type: ignore[return-value]


class RecentActivitySummary(BaseSchema):
    """Recent system activity feed for the overview dashboard."""

    total_events: int = Field(
        ge=0,
        description="Total audit events recorded in the observed activity window",
    )
    activities: list[RecentActivityItem] = Field(
        default_factory=list,
        description="Chronological sequence of recent system activity items (most recent first)",
    )
    generated_at: datetime = Field(
        description="Timestamp in UTC when recent activity was summarized",
    )

    @field_validator("generated_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Section E: Composed Dashboard Overview Response
# ---------------------------------------------------------------------------


class DashboardOverviewResponse(BaseSchema):
    """Composed data contract for the Arogya AI Overview Dashboard.

    Aggregates patient/encounter metrics, analysis run statuses,
    pending review queue metrics, and recent system activities into a single
    strongly-typed response.
    """

    patients: PatientSummary = Field(
        description="Patient cohort summary counts",
    )
    encounters: EncounterSummary = Field(
        description="Clinical encounter summary counts",
    )
    analysis: AnalysisSummary = Field(
        description="AI analysis run totals and status breakdowns",
    )
    reviews: PendingReviewQueueSummary = Field(
        description="Pending clinical review queue metrics",
    )
    recent_activity: RecentActivitySummary = Field(
        description="Recent platform activity entries",
    )
    generated_at: datetime = Field(
        description="UTC timestamp when the complete dashboard payload was composed",
    )
    environment: str = Field(
        default="development",
        description="Runtime environment identifier ('development', 'testing', 'staging', 'production')",
    )

    @field_validator("generated_at")
    @classmethod
    def validate_tz(cls, v: datetime) -> datetime:
        return ensure_timezone_aware(v)  # type: ignore[return-value]
