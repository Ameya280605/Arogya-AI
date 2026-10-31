"""Arogya AI — Overview Dashboard Aggregation Repository.

Module 5, Phase 5.5: Dashboard API Aggregation & Integration.
Performs efficient SQL-level aggregations over clinical domain models
(Patient, Encounter, AnalysisRun, AuditEvent) using SQLAlchemy 2.x select queries.

TRANSACTION OWNERSHIP POLICY:
Follows BaseRepository: Encapsulates query logic without committing or rolling back.
"""

from datetime import date, datetime, time, timezone
from typing import Sequence
from sqlalchemy import String, case, cast, distinct, func, select
from sqlalchemy.orm import Session

from backend.app.db.models import AnalysisRun, AuditEvent, Encounter, Patient
from backend.app.repositories.base import BaseRepository
from backend.app.schemas.dashboard import (
    AnalysisStatusBreakdown,
    AnalysisSummary,
    DashboardOverviewResponse,
    EncounterSummary,
    PatientSummary,
    PendingReviewItem,
    PendingReviewQueueSummary,
    RecentActivityItem,
    RecentActivitySummary,
)


def _to_utc_start(d: date | None) -> datetime | None:
    """Convert an optional date to start-of-day UTC datetime."""
    if d is None:
        return None
    return datetime.combine(d, time.min, tzinfo=timezone.utc)


def _to_utc_end(d: date | None) -> datetime | None:
    """Convert an optional date to end-of-day UTC datetime."""
    if d is None:
        return None
    return datetime.combine(d, time.max, tzinfo=timezone.utc)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure a datetime is timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class DashboardRepository(BaseRepository[None]):
    """Repository executing database aggregations for the Overview Dashboard."""

    def __init__(self, session: Session) -> None:
        """Initialize DashboardRepository with active session."""
        super().__init__(session)

    # -------------------------------------------------------------------------
    # 1. Patient Cohort Aggregation
    # -------------------------------------------------------------------------
    def get_patient_summary(self) -> PatientSummary:
        """Aggregate patient cohort counts by registration category."""
        stmt = select(
            func.count(Patient.id).label("total"),
            func.coalesce(
                func.sum(case((Patient.is_synthetic == True, 1), else_=0)), 0  # noqa: E712
            ).label("synthetic"),
            func.coalesce(
                func.sum(case((Patient.is_synthetic == False, 1), else_=0)), 0  # noqa: E712
            ).label("research"),
        )
        row = self.session.execute(stmt).one()
        total = int(row.total or 0)
        synthetic = int(row.synthetic or 0)
        research = int(row.research or 0)

        # Invariant safety: Ensure sum parity for Pydantic validator
        if total != (synthetic + research):
            synthetic = total - research

        return PatientSummary(
            total_patients=total,
            synthetic_patients=synthetic,
            research_cohort_patients=research,
            generated_at=datetime.now(timezone.utc),
        )

    # -------------------------------------------------------------------------
    # 2. Encounter Status Aggregation
    # -------------------------------------------------------------------------
    def get_encounter_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> EncounterSummary:
        """Aggregate clinical encounters by status with optional date window."""
        start_time = _to_utc_start(start_date)
        end_time = _to_utc_end(end_date)

        stmt = select(
            func.count(Encounter.id).label("total"),
            func.coalesce(
                func.sum(case((Encounter.status == "planned", 1), else_=0)), 0
            ).label("planned"),
            func.coalesce(
                func.sum(case((Encounter.status == "in_progress", 1), else_=0)), 0
            ).label("in_progress"),
            func.coalesce(
                func.sum(case((Encounter.status == "completed", 1), else_=0)), 0
            ).label("completed"),
            func.coalesce(
                func.sum(case((Encounter.status == "cancelled", 1), else_=0)), 0
            ).label("cancelled"),
            func.min(Encounter.start_time).label("min_start"),
            func.max(Encounter.start_time).label("max_start"),
            func.max(Encounter.end_time).label("max_end"),
        )

        if start_time is not None:
            stmt = stmt.where(Encounter.start_time >= start_time)
        if end_time is not None:
            stmt = stmt.where(Encounter.start_time <= end_time)

        row = self.session.execute(stmt).one()
        total = int(row.total or 0)
        planned = int(row.planned or 0)
        in_progress = int(row.in_progress or 0)
        completed = int(row.completed or 0)
        cancelled = int(row.cancelled or 0)

        # Invariant safety: Ensure sum parity
        sum_statuses = planned + in_progress + completed + cancelled
        if total != sum_statuses:
            # If encounters have legacy/unrecognized statuses, bucket them safely
            planned += total - sum_statuses

        period_start: datetime | None = None
        period_end: datetime | None = None

        if total > 0:
            period_start = _ensure_utc(row.min_start)
            period_end = _ensure_utc(row.max_end or row.max_start)
            if (
                period_start is not None
                and period_end is not None
                and period_end < period_start
            ):
                period_end = period_start

        return EncounterSummary(
            total_encounters=total,
            planned=planned,
            in_progress=in_progress,
            completed=completed,
            cancelled=cancelled,
            reporting_period_start=period_start,
            reporting_period_end=period_end,
            generated_at=datetime.now(timezone.utc),
        )

    # -------------------------------------------------------------------------
    # 3. Analysis Run Lifecycle Aggregation
    # -------------------------------------------------------------------------
    def get_analysis_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status_filter: str | None = None,
    ) -> AnalysisSummary:
        """Aggregate analysis runs by execution state with optional filters."""
        start_time = _to_utc_start(start_date)
        end_time = _to_utc_end(end_date)

        stmt = select(
            func.count(AnalysisRun.id).label("total"),
            func.coalesce(
                func.sum(case((AnalysisRun.status == "queued", 1), else_=0)), 0
            ).label("queued"),
            func.coalesce(
                func.sum(case((AnalysisRun.status == "running", 1), else_=0)), 0
            ).label("running"),
            func.coalesce(
                func.sum(case((AnalysisRun.status == "completed", 1), else_=0)), 0
            ).label("completed"),
            func.coalesce(
                func.sum(case((AnalysisRun.status == "failed", 1), else_=0)), 0
            ).label("failed"),
            func.coalesce(
                func.sum(case((AnalysisRun.status == "abstained", 1), else_=0)), 0
            ).label("abstained"),
        )

        if start_time is not None:
            stmt = stmt.where(AnalysisRun.created_at >= start_time)
        if end_time is not None:
            stmt = stmt.where(AnalysisRun.created_at <= end_time)
        if status_filter is not None:
            stmt = stmt.where(AnalysisRun.status == status_filter)

        row = self.session.execute(stmt).one()
        total = int(row.total or 0)
        queued = int(row.queued or 0)
        running = int(row.running or 0)
        completed = int(row.completed or 0)
        failed = int(row.failed or 0)
        abstained = int(row.abstained or 0)

        # Invariant safety: Ensure sum parity
        sum_statuses = queued + running + completed + failed + abstained
        if total != sum_statuses:
            queued += total - sum_statuses

        # Distinct observed models
        models_stmt = select(AnalysisRun.model_name).distinct()
        if start_time is not None:
            models_stmt = models_stmt.where(AnalysisRun.created_at >= start_time)
        if end_time is not None:
            models_stmt = models_stmt.where(AnalysisRun.created_at <= end_time)
        if status_filter is not None:
            models_stmt = models_stmt.where(AnalysisRun.status == status_filter)

        model_rows = self.session.execute(models_stmt).all()
        active_models = sorted([m[0] for m in model_rows if m[0]])

        return AnalysisSummary(
            total_runs=total,
            by_status=AnalysisStatusBreakdown(
                queued=queued,
                running=running,
                completed=completed,
                failed=failed,
                abstained=abstained,
            ),
            active_models_observed=active_models,
            generated_at=datetime.now(timezone.utc),
        )

    # -------------------------------------------------------------------------
    # 4. Review Candidates Queue
    # -------------------------------------------------------------------------
    def get_pending_reviews(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status_filter: str | None = None,
        limit: int = 10,
    ) -> PendingReviewQueueSummary:
        """Retrieve candidate runs requiring clinician triage with bounded preview."""
        start_time = _to_utc_start(start_date)
        end_time = _to_utc_end(end_date)

        # Clinical research definition: review candidates are completed or abstained runs
        candidate_statuses = ["completed", "abstained"]
        if status_filter is not None:
            if status_filter in candidate_statuses:
                candidate_statuses = [status_filter]
            else:
                # If filtered by a status that cannot be a review candidate (queued, running, failed)
                return PendingReviewQueueSummary(
                    pending_count=0,
                    items=[],
                    generated_at=datetime.now(timezone.utc),
                )

        count_stmt = select(func.count(AnalysisRun.id)).where(
            AnalysisRun.status.in_(candidate_statuses)
        )
        items_stmt = select(AnalysisRun).where(
            AnalysisRun.status.in_(candidate_statuses)
        )

        # Exclude runs that have already been formally reviewed
        reviewed_subquery = (
            select(func.replace(AuditEvent.resource_id, "-", ""))
            .where(
                AuditEvent.resource_type == "analysis_run",
                AuditEvent.event_type.ilike("%review%"),
                AuditEvent.resource_id.is_not(None),
            )
        )
        normalized_run_id = func.replace(cast(AnalysisRun.id, String), "-", "")
        count_stmt = count_stmt.where(normalized_run_id.not_in(reviewed_subquery))
        items_stmt = items_stmt.where(normalized_run_id.not_in(reviewed_subquery))

        if start_time is not None:
            count_stmt = count_stmt.where(AnalysisRun.created_at >= start_time)
            items_stmt = items_stmt.where(AnalysisRun.created_at >= start_time)
        if end_time is not None:
            count_stmt = count_stmt.where(AnalysisRun.created_at <= end_time)
            items_stmt = items_stmt.where(AnalysisRun.created_at <= end_time)

        pending_count = int(self.session.execute(count_stmt).scalar() or 0)

        clamped_limit, _ = self._sanitize_pagination(limit=limit, offset=0, max_limit=100)
        items_stmt = items_stmt.order_by(AnalysisRun.created_at.desc()).limit(clamped_limit)
        runs: Sequence[AnalysisRun] = self.session.execute(items_stmt).scalars().all()

        items = [
            PendingReviewItem(
                run_id=run.id,
                patient_id=run.patient_id,
                encounter_id=run.encounter_id,
                model_name=run.model_name,
                model_version=run.model_version,
                status=run.status,
                abstained=(run.status == "abstained"),
                created_at=_ensure_utc(run.created_at),  # type: ignore[arg-type]
            )
            for run in runs
        ]

        return PendingReviewQueueSummary(
            pending_count=pending_count,
            items=items,
            generated_at=datetime.now(timezone.utc),
        )

    # Alias for convenience
    get_pending_review_queue = get_pending_reviews

    # -------------------------------------------------------------------------
    # 5. Recent System Activity Feed
    # -------------------------------------------------------------------------
    def get_recent_activity(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status_filter: str | None = None,
        limit: int = 10,
    ) -> RecentActivitySummary:
        """Retrieve chronological recent audit activity with bounded preview."""
        start_time = _to_utc_start(start_date)
        end_time = _to_utc_end(end_date)

        count_stmt = select(func.count(AuditEvent.id))
        items_stmt = select(AuditEvent)

        if start_time is not None:
            count_stmt = count_stmt.where(AuditEvent.created_at >= start_time)
            items_stmt = items_stmt.where(AuditEvent.created_at >= start_time)
        if end_time is not None:
            count_stmt = count_stmt.where(AuditEvent.created_at <= end_time)
            items_stmt = items_stmt.where(AuditEvent.created_at <= end_time)
        if status_filter is not None:
            count_stmt = count_stmt.where(
                AuditEvent.event_type.like(f"analysis.{status_filter}%")
            )
            items_stmt = items_stmt.where(
                AuditEvent.event_type.like(f"analysis.{status_filter}%")
            )

        total_events = int(self.session.execute(count_stmt).scalar() or 0)

        clamped_limit, _ = self._sanitize_pagination(limit=limit, offset=0, max_limit=100)
        items_stmt = items_stmt.order_by(AuditEvent.created_at.desc()).limit(clamped_limit)
        events: Sequence[AuditEvent] = self.session.execute(items_stmt).scalars().all()

        activities = [
            RecentActivityItem(
                id=evt.id,
                event_type=evt.event_type,
                action=evt.action,
                resource_type=evt.resource_type,
                resource_id=evt.resource_id,
                description=evt.description,
                timestamp=_ensure_utc(evt.created_at),  # type: ignore[arg-type]
            )
            for evt in events
        ]

        return RecentActivitySummary(
            total_events=total_events,
            activities=activities,
            generated_at=datetime.now(timezone.utc),
        )

    # Alias for convenience
    get_recent_activity_summary = get_recent_activity

    # -------------------------------------------------------------------------
    # 6. Complete Dashboard Overview Aggregation
    # -------------------------------------------------------------------------
    def get_overview(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status_filter: str | None = None,
        environment: str = "development",
        limit_previews: int = 10,
    ) -> DashboardOverviewResponse:
        """Compose complete dashboard aggregation response."""
        now = datetime.now(timezone.utc)
        return DashboardOverviewResponse(
            patients=self.get_patient_summary(),
            encounters=self.get_encounter_summary(start_date=start_date, end_date=end_date),
            analysis=self.get_analysis_summary(
                start_date=start_date, end_date=end_date, status_filter=status_filter
            ),
            reviews=self.get_pending_reviews(
                start_date=start_date,
                end_date=end_date,
                status_filter=status_filter,
                limit=limit_previews,
            ),
            recent_activity=self.get_recent_activity(
                start_date=start_date,
                end_date=end_date,
                status_filter=status_filter,
                limit=limit_previews,
            ),
            generated_at=now,
            environment=environment,
        )
