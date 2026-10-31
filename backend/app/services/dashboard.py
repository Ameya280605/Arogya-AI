"""Arogya AI — Dashboard Domain Service.

Module 5, Phase 5.5: Dashboard API Aggregation & Integration.
Orchestrates dashboard telemetry aggregation, validates filter boundaries,
and returns strongly-typed DashboardOverviewResponse models.

GOVERNANCE & SAFETY RULES:
1. Zero PHI: Returned payloads strictly exclude real patient identifiers.
2. Read-Only Aggregation: Does not mutate clinical history or analysis outputs.
3. Transaction Ownership: The caller owns transaction boundaries; this service never commits or rolls back independently.
4. Filter Boundary Validation: Enforces that start_date does not follow end_date and status matches canonical states.
"""

from datetime import date
from sqlalchemy.orm import Session

from backend.app.repositories.dashboard import DashboardRepository
from backend.app.schemas.dashboard import (
    AnalysisRunStatus,
    DashboardOverviewResponse,
)
from backend.app.settings import Settings, get_settings

CANONICAL_ANALYSIS_STATUSES: set[str] = {
    "queued",
    "running",
    "completed",
    "failed",
    "abstained",
}


class DashboardService:
    """Domain service managing dashboard aggregation queries and validation."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
    ) -> None:
        """Initialize DashboardService with active session and repository."""
        self.session = session
        self.repo = DashboardRepository(session)
        self.settings = settings or get_settings()

    def get_overview(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status: AnalysisRunStatus | str | None = None,
        status_filter: AnalysisRunStatus | str | None = None,
        limit_previews: int = 10,
    ) -> DashboardOverviewResponse:
        """Validate filter boundaries and aggregate complete dashboard telemetry.

        Args:
            start_date: Optional start date boundary in UTC.
            end_date: Optional end date boundary in UTC.
            status: Optional analysis run lifecycle status filter.
            status_filter: Optional alias for status filter.
            limit_previews: Maximum number of preview items to include in queue/activity feeds.

        Returns:
            Validated DashboardOverviewResponse matching Phase 5.1 data contract.

        Raises:
            ValueError: If start_date > end_date or status is invalid.
        """
        # Validate date range
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                raise ValueError(
                    f"Invalid date range: start_date ({start_date}) cannot follow end_date ({end_date})"
                )

        # Resolve status filter from either status or status_filter argument
        raw_status = status_filter if status_filter is not None else status
        resolved_status: str | None = None
        if raw_status is not None:
            cleaned_status = str(raw_status).strip().lower()
            if cleaned_status not in CANONICAL_ANALYSIS_STATUSES:
                raise ValueError(
                    f"Invalid analysis run status filter '{raw_status}'. Must be one of: "
                    f"{', '.join(sorted(CANONICAL_ANALYSIS_STATUSES))}"
                )
            resolved_status = cleaned_status

        return self.repo.get_overview(
            start_date=start_date,
            end_date=end_date,
            status_filter=resolved_status,
            environment=self.settings.app_env,
            limit_previews=limit_previews,
        )
