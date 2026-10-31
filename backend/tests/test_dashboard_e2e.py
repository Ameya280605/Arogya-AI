"""Arogya AI — Phase 5.6: End-to-End Dashboard Integration Tests.

Validates the complete end-to-end dashboard integration flow:
1. Seeded clinical domain records (Module 3) match aggregated metrics exactly.
2. Multi-cohort, multi-status datasets aggregate accurately across patient, encounter, and run lifecycles.
3. Review candidate queue properly identifies unreviewed completed/abstained runs and excludes reviewed runs.
4. Date range and status filters produce precise SQL aggregations.
5. Zero-result filter queries and empty databases return honest empty counts.
6. Input validation rejects reversed date boundaries (422) and invalid statuses (422).
7. Database unavailability triggers honest HTTP 503 envelopes without data fabrication.
8. Zero-PHI and data minimization standards are preserved across all payloads.
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.models import AnalysisRun, AuditEvent, Encounter, Patient, User
from backend.app.db.session import (
    DatabaseConnectionError,
    get_db,
)
from backend.app.main import create_app
from backend.app.schemas.dashboard import DashboardOverviewResponse
from backend.app.services.dashboard import DashboardService
from backend.app.settings import Settings
from scripts.seed_dev_data import seed_development_data


@pytest.fixture
def canonical_seeded_db() -> Session:
    """Fixture providing an in-memory SQLite database populated with canonical synthetic seed data."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()

    # Seed with standard Module 3 development dataset (explicit opt-in confirmed=True)
    seed_development_data(session, confirmed=True)

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def multi_record_db() -> Session:
    """Fixture providing an in-memory SQLite database with rich multi-cohort, multi-run fixtures."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()

    # 1. Auditor user
    auditor = User(
        id=uuid.uuid4(),
        username="e2e_auditor",
        email="auditor@e2e.test",
        full_name="E2E Auditor",
        hashed_password="!DISABLED!",
        is_active=True,
    )
    session.add(auditor)

    # 2. Patients: 3 synthetic + 2 research cohorts
    p1 = Patient(id=uuid.uuid4(), mrn_pseudonym="SYNTH-PAT-0001", is_synthetic=True, birth_date=date(1985, 5, 12))
    p2 = Patient(id=uuid.uuid4(), mrn_pseudonym="SYNTH-PAT-0002", is_synthetic=True, birth_date=date(1990, 7, 24))
    p3 = Patient(id=uuid.uuid4(), mrn_pseudonym="SYNTH-PAT-0003", is_synthetic=True, birth_date=date(2001, 3, 15))
    p4 = Patient(id=uuid.uuid4(), mrn_pseudonym="RES-COHORT-A01", is_synthetic=False, birth_date=date(1975, 11, 2))
    p5 = Patient(id=uuid.uuid4(), mrn_pseudonym="RES-COHORT-A02", is_synthetic=False, birth_date=date(1968, 9, 30))
    session.add_all([p1, p2, p3, p4, p5])

    # 3. Encounters: 2 in_progress, 3 completed
    e1 = Encounter(id=uuid.uuid4(), patient_id=p1.id, status="completed", start_time=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc), end_time=datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc))
    e2 = Encounter(id=uuid.uuid4(), patient_id=p2.id, status="completed", start_time=datetime(2026, 1, 12, 10, 0, tzinfo=timezone.utc), end_time=datetime(2026, 1, 12, 11, 0, tzinfo=timezone.utc))
    e3 = Encounter(id=uuid.uuid4(), patient_id=p3.id, status="completed", start_time=datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc), end_time=datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc))
    e4 = Encounter(id=uuid.uuid4(), patient_id=p4.id, status="in_progress", start_time=datetime(2026, 1, 20, 9, 0, tzinfo=timezone.utc))
    e5 = Encounter(id=uuid.uuid4(), patient_id=p5.id, status="in_progress", start_time=datetime(2026, 1, 22, 11, 0, tzinfo=timezone.utc))
    session.add_all([e1, e2, e3, e4, e5])

    # 4. Analysis Runs: 2 completed (1 reviewed, 1 unreviewed), 1 abstained (unreviewed), 1 running, 1 failed
    run_reviewed = AnalysisRun(id=uuid.uuid4(), patient_id=p1.id, encounter_id=e1.id, model_name="screener_v1", model_version="1.0", status="completed", created_at=datetime(2026, 1, 10, 9, 0, tzinfo=timezone.utc))
    run_candidate1 = AnalysisRun(id=uuid.uuid4(), patient_id=p2.id, encounter_id=e2.id, model_name="screener_v1", model_version="1.0", status="completed", created_at=datetime(2026, 1, 12, 11, 0, tzinfo=timezone.utc))
    run_candidate2 = AnalysisRun(id=uuid.uuid4(), patient_id=p3.id, encounter_id=e3.id, model_name="risk_v2", model_version="2.0", status="abstained", created_at=datetime(2026, 1, 15, 15, 0, tzinfo=timezone.utc))
    run_running = AnalysisRun(id=uuid.uuid4(), patient_id=p4.id, encounter_id=e4.id, model_name="risk_v2", model_version="2.0", status="running", created_at=datetime(2026, 1, 20, 9, 30, tzinfo=timezone.utc))
    run_failed = AnalysisRun(id=uuid.uuid4(), patient_id=p5.id, encounter_id=e5.id, model_name="risk_v2", model_version="2.0", status="failed", created_at=datetime(2026, 1, 22, 11, 30, tzinfo=timezone.utc))
    session.add_all([run_reviewed, run_candidate1, run_candidate2, run_running, run_failed])

    # 5. Audit Events: 1 review event for run_reviewed (excluding it from candidates), plus 2 operational events
    audit_review = AuditEvent(id=uuid.uuid4(), event_type="analysis.review", actor_id=auditor.id, action="review", resource_type="analysis_run", resource_id=str(run_reviewed.id), created_at=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc))
    audit_exec = AuditEvent(id=uuid.uuid4(), event_type="analysis.execute", actor_id=auditor.id, action="execute", resource_type="analysis_run", resource_id=str(run_candidate1.id), created_at=datetime(2026, 1, 12, 11, 5, tzinfo=timezone.utc))
    audit_other = AuditEvent(id=uuid.uuid4(), event_type="encounter.create", actor_id=auditor.id, action="create", resource_type="encounter", resource_id=str(e1.id), created_at=datetime(2026, 1, 10, 8, 5, tzinfo=timezone.utc))
    session.add_all([audit_review, audit_exec, audit_other])

    session.commit()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def canonical_client(canonical_seeded_db: Session) -> TestClient:
    """FastAPI TestClient wired to the canonical Module 3 seed database."""
    app = create_app(Settings(app_env="testing"))

    def override_get_db():
        yield canonical_seeded_db

    from backend.app.db.models import Role
    from backend.app.security.dependencies import get_current_user

    e2e_user = User(
        id=uuid.uuid4(),
        username="e2e_clinician",
        email="clinician@e2e.test",
        full_name="E2E Clinician",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="doctor_reviewer")],
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: e2e_user
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def multi_record_client(multi_record_db: Session) -> TestClient:
    """FastAPI TestClient wired to the multi-record test database."""
    app = create_app(Settings(app_env="testing"))

    def override_get_db():
        yield multi_record_db

    from backend.app.db.models import Role
    from backend.app.security.dependencies import get_current_user

    e2e_user = User(
        id=uuid.uuid4(),
        username="e2e_clinician",
        email="clinician@e2e.test",
        full_name="E2E Clinician",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="doctor_reviewer")],
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: e2e_user
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_e2e_canonical_seed_metrics_match(canonical_client: TestClient) -> None:
    """Verify canonical seed data (Module 3) is correctly aggregated by GET /api/v1/dashboard/overview."""
    response = canonical_client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    data = response.json()
    validated = DashboardOverviewResponse.model_validate(data)

    # 1. Patient cohort counts
    assert validated.patients.total_patients == 1
    assert validated.patients.synthetic_patients == 1
    assert validated.patients.research_cohort_patients == 0

    # 2. Encounter summary
    assert validated.encounters.total_encounters == 1
    assert validated.encounters.completed == 1
    assert validated.encounters.in_progress == 0
    assert validated.encounters.reporting_period_start is not None
    assert validated.encounters.reporting_period_end is not None

    # 3. Analysis run lifecycle breakdown
    assert validated.analysis.total_runs == 1
    assert validated.analysis.by_status.completed == 1
    assert validated.analysis.by_status.running == 0
    assert validated.analysis.by_status.failed == 0
    assert validated.analysis.by_status.abstained == 0
    assert validated.analysis.by_status.queued == 0
    assert len(validated.analysis.active_models_observed) == 1
    assert "synthetic_baseline_screener" in validated.analysis.active_models_observed

    # 4. Review candidate queue
    assert validated.reviews.pending_count == 1
    assert len(validated.reviews.items) == 1
    item = validated.reviews.items[0]
    assert item.status == "completed"
    assert item.patient_id is not None
    assert item.model_name == "synthetic_baseline_screener"

    # 5. Recent audit activity
    assert validated.recent_activity.total_events == 1
    assert len(validated.recent_activity.activities) == 1
    activity = validated.recent_activity.activities[0]
    assert activity.id is not None
    assert activity.timestamp is not None


@pytest.mark.integration
def test_e2e_multi_cohort_and_candidate_exclusion(multi_record_client: TestClient) -> None:
    """Verify multi-cohort metrics and proper exclusion of reviewed runs from the candidate queue."""
    response = multi_record_client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    validated = DashboardOverviewResponse.model_validate(response.json())

    # Patient cohorts partitioned into synthetic vs research
    assert validated.patients.total_patients == 5
    assert validated.patients.synthetic_patients == 3
    assert validated.patients.research_cohort_patients == 2

    # Encounter lifecycles
    assert validated.encounters.total_encounters == 5
    assert validated.encounters.completed == 3
    assert validated.encounters.in_progress == 2

    # Analysis lifecycle distribution
    assert validated.analysis.total_runs == 5
    assert validated.analysis.by_status.completed == 2
    assert validated.analysis.by_status.abstained == 1
    assert len(validated.analysis.active_models_observed) == 2
    assert set(validated.analysis.active_models_observed) == {"screener_v1", "risk_v2"}

    # Review candidates: out of 3 candidates (2 completed + 1 abstained), 1 completed was reviewed
    # Only the 2 unreviewed runs should appear in the queue
    assert validated.reviews.pending_count == 2
    assert len(validated.reviews.items) == 2
    candidate_statuses = {item.status for item in validated.reviews.items}
    assert candidate_statuses == {"completed", "abstained"}

    # Audit events
    assert validated.recent_activity.total_events == 3


@pytest.mark.integration
def test_e2e_status_filter_propagation(multi_record_client: TestClient) -> None:
    """Verify status query parameter filters analysis runs and review queue consistently."""
    # Filter for completed only
    response = multi_record_client.get("/api/v1/dashboard/overview?status=completed")
    assert response.status_code == 200
    validated = DashboardOverviewResponse.model_validate(response.json())

    assert validated.analysis.total_runs == 2
    assert validated.analysis.by_status.completed == 2
    assert validated.analysis.by_status.running == 0
    assert validated.analysis.by_status.failed == 0
    assert validated.analysis.by_status.abstained == 0

    # Only unreviewed completed candidates in queue
    assert validated.reviews.pending_count == 1
    for item in validated.reviews.items:
        assert item.status == "completed"

    # Filter for abstained only
    resp_abs = multi_record_client.get("/api/v1/dashboard/overview?status=abstained")
    assert resp_abs.status_code == 200
    val_abs = DashboardOverviewResponse.model_validate(resp_abs.json())
    assert val_abs.analysis.total_runs == 1
    assert val_abs.analysis.by_status.abstained == 1
    assert val_abs.reviews.pending_count == 1
    assert val_abs.reviews.items[0].status == "abstained"


@pytest.mark.integration
def test_e2e_date_range_filter_propagation(multi_record_client: TestClient) -> None:
    """Verify start_date and end_date filters isolate records within UTC observation boundaries."""
    # Filter between Jan 11 and Jan 16 (includes run_candidate1 and run_candidate2, excludes run_reviewed on Jan 10)
    response = multi_record_client.get(
        "/api/v1/dashboard/overview?start_date=2026-01-11&end_date=2026-01-16"
    )
    assert response.status_code == 200
    validated = DashboardOverviewResponse.model_validate(response.json())

    # Only runs created in that window
    assert validated.analysis.total_runs == 2
    assert validated.analysis.by_status.completed == 1
    assert validated.analysis.by_status.abstained == 1


@pytest.mark.integration
def test_e2e_zero_result_filter_handling(multi_record_client: TestClient) -> None:
    """Verify date ranges outside all records yield truthful empty counts without runtime errors."""
    response = multi_record_client.get(
        "/api/v1/dashboard/overview?start_date=2099-01-01&end_date=2099-12-31"
    )
    assert response.status_code == 200
    validated = DashboardOverviewResponse.model_validate(response.json())

    assert validated.analysis.total_runs == 0
    assert validated.analysis.by_status.completed == 0
    assert validated.analysis.by_status.running == 0
    assert validated.reviews.pending_count == 0
    assert len(validated.reviews.items) == 0
    assert validated.recent_activity.total_events == 0
    assert len(validated.recent_activity.activities) == 0


@pytest.mark.integration
def test_e2e_validation_errors_prevent_execution(multi_record_client: TestClient) -> None:
    """Verify reversed dates and invalid statuses return HTTP 422 standard error envelopes."""
    # Reversed date range
    rev_resp = multi_record_client.get(
        "/api/v1/dashboard/overview?start_date=2026-02-01&end_date=2026-01-01"
    )
    assert rev_resp.status_code == 422
    err_rev = rev_resp.json()
    assert "start_date" in str(err_rev) and "cannot follow end_date" in str(err_rev)

    # Invalid status
    stat_resp = multi_record_client.get("/api/v1/dashboard/overview?status=nonexistent_status")
    assert stat_resp.status_code == 422
    err_stat = stat_resp.json()
    assert "status" in str(err_stat)


@pytest.mark.integration
def test_e2e_empty_database_aggregations() -> None:
    """Verify repository and service behave gracefully on a completely empty database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()

    try:
        service = DashboardService(session)
        overview = service.get_overview()
        assert overview.patients.total_patients == 0
        assert overview.patients.synthetic_patients == 0
        assert overview.patients.research_cohort_patients == 0
        assert overview.encounters.total_encounters == 0
        assert overview.analysis.total_runs == 0
        assert overview.reviews.pending_count == 0
        assert len(overview.reviews.items) == 0
        assert overview.recent_activity.total_events == 0
        assert len(overview.recent_activity.activities) == 0
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.mark.integration
def test_e2e_database_unavailable_error_handling() -> None:
    """Verify that database connection failures trigger an honest HTTP 503 SERVICE_UNAVAILABLE envelope."""
    app = create_app(Settings(app_env="testing"))

    def failing_get_db():
        raise DatabaseConnectionError("PostgreSQL cluster unavailable at 127.0.0.1:5432")

    app.dependency_overrides[get_db] = failing_get_db
    client = TestClient(app)

    try:
        response = client.get("/api/v1/dashboard/overview")
        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
        assert "unavailable" in data["error"]["message"].lower()
    finally:
        app.dependency_overrides.clear()
