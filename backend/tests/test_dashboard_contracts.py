"""Arogya AI - Overview Dashboard Data Contract Unit Tests.

Module 5, Phase 5.1: Dashboard Data Contracts.
Validates Pydantic contracts for the Overview Dashboard:
- Patient and encounter cohort summaries with non-negative constraints.
- Analysis-run totals and status breakdown consistency.
- Pending review queue counts, candidate item previews, and pagination.
- Sanitized recent system activity telemetry.
- Composed DashboardOverviewResponse serialization and JSON compatibility.
- Rejection of negative counts, invalid dates, and extra payload fields.
- Non-PHI and security compliance.
"""

from datetime import datetime, timedelta, timezone
import json
import uuid
import pytest
from pydantic import ValidationError

from backend.app.errors import ErrorFieldDetail, ErrorPayload, ErrorResponse
from backend.app.schemas.dashboard import (
    AnalysisRunStatus,
    AnalysisStatusBreakdown,
    AnalysisSummary,
    DashboardOverviewResponse,
    EncounterSummary,
    PatientSummary,
    PendingReviewItem,
    PendingReviewQueuePaginated,
    PendingReviewQueueSummary,
    RecentActivityItem,
    RecentActivitySummary,
)


@pytest.fixture
def sample_utc_now() -> datetime:
    """Provide a consistent timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# 1. Patient Summary Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_patient_summary_valid(sample_utc_now: datetime) -> None:
    """Verify valid construction of PatientSummary with non-negative counts."""
    summary = PatientSummary(
        total_patients=100,
        synthetic_patients=80,
        research_cohort_patients=20,
        generated_at=sample_utc_now,
    )
    assert summary.total_patients == 100
    assert summary.synthetic_patients == 80
    assert summary.research_cohort_patients == 20
    assert summary.generated_at == sample_utc_now


@pytest.mark.unit
def test_patient_summary_zero_counts_valid(sample_utc_now: datetime) -> None:
    """Verify that zero counts are valid distinct numbers and not treated as missing."""
    summary = PatientSummary(
        total_patients=0,
        synthetic_patients=0,
        research_cohort_patients=0,
        generated_at=sample_utc_now,
    )
    assert summary.total_patients == 0
    assert summary.synthetic_patients == 0
    assert summary.research_cohort_patients == 0


@pytest.mark.unit
def test_patient_summary_rejection_of_negative_counts(sample_utc_now: datetime) -> None:
    """Verify rejection of negative integers in patient summary fields."""
    with pytest.raises(ValidationError) as exc_info:
        PatientSummary(
            total_patients=-1,
            synthetic_patients=0,
            research_cohort_patients=-1,
            generated_at=sample_utc_now,
        )
    errors = exc_info.value.errors()
    assert any("greater than or equal to 0" in e["msg"] for e in errors)


@pytest.mark.unit
def test_patient_summary_cohort_sum_consistency(sample_utc_now: datetime) -> None:
    """Verify that total_patients must equal synthetic + research cohort counts."""
    with pytest.raises(ValidationError) as exc_info:
        PatientSummary(
            total_patients=100,
            synthetic_patients=50,
            research_cohort_patients=40,  # 50 + 40 != 100
            generated_at=sample_utc_now,
        )
    assert "must equal the sum of synthetic_patients" in str(exc_info.value)


@pytest.mark.unit
def test_patient_summary_naive_datetime_rejected() -> None:
    """Verify that timezone-naive datetime is rejected."""
    naive_dt = datetime(2026, 10, 26, 12, 0, 0)
    with pytest.raises(ValidationError) as exc_info:
        PatientSummary(
            total_patients=10,
            synthetic_patients=10,
            research_cohort_patients=0,
            generated_at=naive_dt,
        )
    assert "must be timezone-aware" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 2. Encounter Summary Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_encounter_summary_valid(sample_utc_now: datetime) -> None:
    """Verify valid construction of EncounterSummary with status breakdown."""
    start_dt = sample_utc_now - timedelta(days=30)
    summary = EncounterSummary(
        total_encounters=25,
        planned=5,
        in_progress=3,
        completed=15,
        cancelled=2,
        reporting_period_start=start_dt,
        reporting_period_end=sample_utc_now,
        generated_at=sample_utc_now,
    )
    assert summary.total_encounters == 25
    assert summary.planned == 5
    assert summary.in_progress == 3
    assert summary.completed == 15
    assert summary.cancelled == 2
    assert summary.reporting_period_start == start_dt
    assert summary.reporting_period_end == sample_utc_now


@pytest.mark.unit
def test_encounter_summary_zero_counts_valid(sample_utc_now: datetime) -> None:
    """Verify valid zero counts in encounter summary."""
    summary = EncounterSummary(
        total_encounters=0,
        planned=0,
        in_progress=0,
        completed=0,
        cancelled=0,
        generated_at=sample_utc_now,
    )
    assert summary.total_encounters == 0
    assert summary.reporting_period_start is None
    assert summary.reporting_period_end is None


@pytest.mark.unit
def test_encounter_summary_rejection_of_negative_counts(sample_utc_now: datetime) -> None:
    """Verify rejection of negative integers in encounter counts."""
    with pytest.raises(ValidationError):
        EncounterSummary(
            total_encounters=-5,
            planned=0,
            in_progress=0,
            completed=0,
            cancelled=0,
            generated_at=sample_utc_now,
        )


@pytest.mark.unit
def test_encounter_summary_sum_consistency(sample_utc_now: datetime) -> None:
    """Verify total_encounters must equal sum of status counts."""
    with pytest.raises(ValidationError) as exc_info:
        EncounterSummary(
            total_encounters=30,
            planned=10,
            in_progress=5,
            completed=10,
            cancelled=0,  # 10 + 5 + 10 + 0 = 25 != 30
            generated_at=sample_utc_now,
        )
    assert "must equal sum of status counts" in str(exc_info.value)


@pytest.mark.unit
def test_encounter_summary_period_order_validation(sample_utc_now: datetime) -> None:
    """Verify that reporting_period_end cannot precede reporting_period_start."""
    with pytest.raises(ValidationError) as exc_info:
        EncounterSummary(
            total_encounters=0,
            planned=0,
            in_progress=0,
            completed=0,
            cancelled=0,
            reporting_period_start=sample_utc_now,
            reporting_period_end=sample_utc_now - timedelta(hours=1),
            generated_at=sample_utc_now,
        )
    assert "reporting_period_end cannot precede reporting_period_start" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 3. Analysis Summary Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_analysis_summary_valid(sample_utc_now: datetime) -> None:
    """Verify valid construction of AnalysisSummary with status distribution."""
    breakdown = AnalysisStatusBreakdown(
        queued=2,
        running=1,
        completed=15,
        failed=1,
        abstained=1,
    )
    summary = AnalysisSummary(
        total_runs=20,
        by_status=breakdown,
        active_models_observed=["cxr_densenet121_baseline", "tabular_xgb_risk"],
        generated_at=sample_utc_now,
    )
    assert summary.total_runs == 20
    assert summary.by_status.completed == 15
    assert summary.by_status.abstained == 1
    assert len(summary.active_models_observed) == 2


@pytest.mark.unit
def test_analysis_summary_status_sum_consistency(sample_utc_now: datetime) -> None:
    """Verify total_runs must equal sum of breakdown counts."""
    breakdown = AnalysisStatusBreakdown(
        queued=1,
        running=0,
        completed=5,
        failed=0,
        abstained=0,
    )
    with pytest.raises(ValidationError) as exc_info:
        AnalysisSummary(
            total_runs=10,  # 6 != 10
            by_status=breakdown,
            generated_at=sample_utc_now,
        )
    assert "must equal sum of status counts" in str(exc_info.value)


@pytest.mark.unit
def test_analysis_summary_rejection_of_negative_breakdown(sample_utc_now: datetime) -> None:
    """Verify rejection of negative numbers in breakdown fields."""
    with pytest.raises(ValidationError):
        AnalysisStatusBreakdown(
            queued=-1,
            running=0,
            completed=0,
            failed=0,
            abstained=0,
        )


# ---------------------------------------------------------------------------
# 4. Pending Review Queue Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pending_review_item_valid(sample_utc_now: datetime) -> None:
    """Verify valid construction of PendingReviewItem with UUID identifiers."""
    run_id = uuid.uuid4()
    patient_id = uuid.uuid4()
    item = PendingReviewItem(
        run_id=run_id,
        patient_id=patient_id,
        encounter_id=None,
        model_name="cxr_densenet121_baseline",
        model_version="1.0.0",
        status="completed",
        abstained=False,
        created_at=sample_utc_now,
    )
    assert item.run_id == run_id
    assert item.patient_id == patient_id
    assert item.encounter_id is None
    assert item.model_name == "cxr_densenet121_baseline"
    assert item.status == "completed"
    assert item.abstained is False


@pytest.mark.unit
def test_pending_review_queue_summary_valid(sample_utc_now: datetime) -> None:
    """Verify valid PendingReviewQueueSummary with empty and populated items."""
    # Empty list
    empty_summary = PendingReviewQueueSummary(
        pending_count=0,
        items=[],
        generated_at=sample_utc_now,
    )
    assert empty_summary.pending_count == 0
    assert len(empty_summary.items) == 0

    # Populated list
    item = PendingReviewItem(
        run_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        model_name="tabular_risk_baseline",
        model_version="0.1.0",
        status="abstained",
        abstained=True,
        created_at=sample_utc_now,
    )
    populated_summary = PendingReviewQueueSummary(
        pending_count=1,
        items=[item],
        generated_at=sample_utc_now,
    )
    assert populated_summary.pending_count == 1
    assert len(populated_summary.items) == 1
    assert populated_summary.items[0].abstained is True


@pytest.mark.unit
def test_pending_review_queue_paginated(sample_utc_now: datetime) -> None:
    """Verify PaginatedResponse envelope compatibility for review queue."""
    item = PendingReviewItem(
        run_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        model_name="cxr_densenet121",
        model_version="1.0.0",
        status="completed",
        abstained=False,
        created_at=sample_utc_now,
    )
    paginated = PendingReviewQueuePaginated(
        items=[item],
        total=1,
        page=1,
        page_size=10,
    )
    assert paginated.total == 1
    assert paginated.page == 1
    assert paginated.page_size == 10
    assert len(paginated.items) == 1


# ---------------------------------------------------------------------------
# 5. Recent Activity Contract Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_recent_activity_item_valid(sample_utc_now: datetime) -> None:
    """Verify valid RecentActivityItem construction."""
    act_id = uuid.uuid4()
    item = RecentActivityItem(
        id=act_id,
        event_type="analysis.started",
        action="execute",
        resource_type="analysis_run",
        resource_id=str(uuid.uuid4()),
        description="Initiated baseline chest X-ray evaluation",
        timestamp=sample_utc_now,
    )
    assert item.id == act_id
    assert item.event_type == "analysis.started"
    assert item.action == "execute"
    assert item.resource_type == "analysis_run"
    assert item.timestamp == sample_utc_now


@pytest.mark.unit
def test_recent_activity_summary_valid(sample_utc_now: datetime) -> None:
    """Verify valid RecentActivitySummary with zero and populated counts."""
    # Zero activity
    empty_summary = RecentActivitySummary(
        total_events=0,
        activities=[],
        generated_at=sample_utc_now,
    )
    assert empty_summary.total_events == 0
    assert len(empty_summary.activities) == 0

    # Populated activity
    item = RecentActivityItem(
        id=uuid.uuid4(),
        event_type="case.created",
        action="create",
        resource_type="patient",
        resource_id="SYNTH-PAT-0001",
        description="Registered synthetic patient case",
        timestamp=sample_utc_now,
    )
    summary = RecentActivitySummary(
        total_events=1,
        activities=[item],
        generated_at=sample_utc_now,
    )
    assert summary.total_events == 1
    assert len(summary.activities) == 1


@pytest.mark.unit
def test_recent_activity_no_phi_leakage() -> None:
    """Verify that RecentActivityItem strictly forbids arbitrary extra fields (e.g. passwords, PHI)."""
    with pytest.raises(ValidationError):
        RecentActivityItem(
            id=uuid.uuid4(),
            event_type="user.login",
            action="execute",
            timestamp=datetime.now(timezone.utc),
            password_hash="secret",  # Extra forbidden field
        )


# ---------------------------------------------------------------------------
# 6. Composed Dashboard Overview Response Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_overview_response_valid(sample_utc_now: datetime) -> None:
    """Verify composition, serialization, and deserialization of DashboardOverviewResponse."""
    overview = DashboardOverviewResponse(
        patients=PatientSummary(
            total_patients=50,
            synthetic_patients=40,
            research_cohort_patients=10,
            generated_at=sample_utc_now,
        ),
        encounters=EncounterSummary(
            total_encounters=12,
            planned=2,
            in_progress=2,
            completed=7,
            cancelled=1,
            generated_at=sample_utc_now,
        ),
        analysis=AnalysisSummary(
            total_runs=10,
            by_status=AnalysisStatusBreakdown(
                queued=1,
                running=1,
                completed=7,
                failed=1,
                abstained=0,
            ),
            active_models_observed=["tabular_risk_model"],
            generated_at=sample_utc_now,
        ),
        reviews=PendingReviewQueueSummary(
            pending_count=0,
            items=[],
            generated_at=sample_utc_now,
        ),
        recent_activity=RecentActivitySummary(
            total_events=0,
            activities=[],
            generated_at=sample_utc_now,
        ),
        generated_at=sample_utc_now,
        environment="development",
    )

    assert overview.patients.total_patients == 50
    assert overview.encounters.total_encounters == 12
    assert overview.analysis.total_runs == 10
    assert overview.reviews.pending_count == 0
    assert overview.recent_activity.total_events == 0
    assert overview.environment == "development"

    # Test serialization to dict
    as_dict = overview.model_dump()
    assert as_dict["patients"]["total_patients"] == 50
    assert as_dict["environment"] == "development"

    # Test JSON round-trip compatibility
    json_str = overview.model_dump_json()
    parsed = json.loads(json_str)
    assert parsed["patients"]["total_patients"] == 50
    assert parsed["encounters"]["completed"] == 7

    # Test deserialization from JSON
    reconstituted = DashboardOverviewResponse.model_validate_json(json_str)
    assert reconstituted.patients.total_patients == 50
    assert reconstituted.encounters.completed == 7
    assert reconstituted.analysis.by_status.completed == 7


@pytest.mark.unit
def test_dashboard_extra_fields_forbidden(sample_utc_now: datetime) -> None:
    """Verify that unexpected extra payload attributes are strictly forbidden."""
    with pytest.raises(ValidationError) as exc_info:
        PatientSummary(
            total_patients=10,
            synthetic_patients=10,
            research_cohort_patients=0,
            generated_at=sample_utc_now,
            unexpected_diagnostic_score=99.5,  # Forbidden extra field
        )
    assert "extra_forbidden" in str(exc_info.value)


@pytest.mark.unit
def test_error_response_compatibility() -> None:
    """Verify that dashboard error scenarios adhere to the standard ErrorResponse envelope."""
    error = ErrorResponse(
        error=ErrorPayload(
            code="DASHBOARD_DATABASE_UNAVAILABLE",
            message="Unable to aggregate overview metrics from database",
            request_id="req-test-123",
            details=[
                ErrorFieldDetail(
                    loc=["database", "connection"],
                    msg="Connection timeout",
                    type="service_unavailable",
                )
            ],
        )
    )
    assert error.error.code == "DASHBOARD_DATABASE_UNAVAILABLE"
    assert error.error.request_id == "req-test-123"
    assert error.error.details is not None
    assert len(error.error.details) == 1
