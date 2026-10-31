"""Arogya AI — Dashboard Repository Unit Tests.

Module 5, Phase 5.5: Dashboard API Aggregation & Integration.
Tests database-level SQL aggregations across Patient, Encounter, AnalysisRun,
and AuditEvent models under SQLite in-memory persistence.
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.models import (
    AnalysisRun,
    AuditEvent,
    Encounter,
    Patient,
    User,
)
from backend.app.repositories.dashboard import DashboardRepository


@pytest.fixture
def db_session() -> Session:
    """Fixture providing an isolated in-memory SQLite database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def repo(db_session: Session) -> DashboardRepository:
    """Provide a DashboardRepository instance bound to the isolated session."""
    return DashboardRepository(session=db_session)


@pytest.fixture
def sample_patient(db_session: Session) -> Patient:
    """Create a persistent patient record for foreign key associations."""
    p = Patient(
        id=uuid.uuid4(),
        mrn_pseudonym="SYNTH-PAT-0001",
        birth_date=date(1980, 5, 12),
        biological_sex="male",
        is_synthetic=True,
    )
    db_session.add(p)
    db_session.commit()
    return p


@pytest.fixture
def sample_user(db_session: Session) -> User:
    """Create a persistent user record for audit associations."""
    u = User(
        id=uuid.uuid4(),
        username="test_auditor",
        email="test_auditor@arogya.local",
        hashed_password="dummy_hashed_password",
        full_name="Audit Reviewer",
        is_active=True,
    )
    db_session.add(u)
    db_session.commit()
    return u


def test_empty_database_aggregations(repo: DashboardRepository):
    """Verify that an empty database aggregates to non-negative zeros and null periods."""
    patients = repo.get_patient_summary()
    assert patients.total_patients == 0
    assert patients.synthetic_patients == 0
    assert patients.research_cohort_patients == 0
    assert patients.generated_at is not None

    encounters = repo.get_encounter_summary()
    assert encounters.total_encounters == 0
    assert encounters.planned == 0
    assert encounters.in_progress == 0
    assert encounters.completed == 0
    assert encounters.cancelled == 0
    assert encounters.reporting_period_start is None
    assert encounters.reporting_period_end is None

    analysis = repo.get_analysis_summary()
    assert analysis.total_runs == 0
    assert analysis.by_status.queued == 0
    assert analysis.by_status.running == 0
    assert analysis.by_status.completed == 0
    assert analysis.by_status.failed == 0
    assert analysis.by_status.abstained == 0
    assert analysis.active_models_observed == []

    reviews = repo.get_pending_review_queue()
    assert reviews.pending_count == 0
    assert reviews.items == []

    activity = repo.get_recent_activity_summary()
    assert activity.total_events == 0
    assert activity.activities == []


def test_patient_cohort_aggregation(db_session: Session, repo: DashboardRepository):
    """Verify patient cohort counts partition synthetic vs research cohort correctly."""
    p1 = Patient(id=uuid.uuid4(), mrn_pseudonym="SYNTH-PAT-1", is_synthetic=True)
    p2 = Patient(id=uuid.uuid4(), mrn_pseudonym="SYNTH-PAT-2", is_synthetic=True)
    p3 = Patient(id=uuid.uuid4(), mrn_pseudonym="SYNTH-PAT-3", is_synthetic=True)
    p4 = Patient(id=uuid.uuid4(), mrn_pseudonym="RES-PAT-1", is_synthetic=False)
    p5 = Patient(id=uuid.uuid4(), mrn_pseudonym="RES-PAT-2", is_synthetic=False)

    db_session.add_all([p1, p2, p3, p4, p5])
    db_session.commit()

    summary = repo.get_patient_summary()
    assert summary.total_patients == 5
    assert summary.synthetic_patients == 3
    assert summary.research_cohort_patients == 2


def test_encounter_status_aggregation_and_reporting_period(
    db_session: Session, repo: DashboardRepository, sample_patient: Patient
):
    """Verify encounter status breakdown and reporting window extraction."""
    t1 = datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 12, 12, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 1, 15, 17, 0, tzinfo=timezone.utc)

    e1 = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="ambulatory",
        status="planned",
        start_time=t1,
        end_time=None,
    )
    e2 = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="emergency",
        status="in_progress",
        start_time=t1,
        end_time=None,
    )
    e3 = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="inpatient",
        status="completed",
        start_time=t2,
        end_time=t3,
    )
    e4 = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="telehealth",
        status="cancelled",
        start_time=t2,
        end_time=None,
    )

    db_session.add_all([e1, e2, e3, e4])
    db_session.commit()

    summary = repo.get_encounter_summary()
    assert summary.total_encounters == 4
    assert summary.planned == 1
    assert summary.in_progress == 1
    assert summary.completed == 1
    assert summary.cancelled == 1
    assert summary.reporting_period_start == t1
    assert summary.reporting_period_end == t3


def test_analysis_run_status_and_models_aggregation(
    db_session: Session, repo: DashboardRepository, sample_patient: Patient
):
    """Verify analysis run status counts and distinct active model observation."""
    now = datetime(2026, 1, 20, 10, 0, tzinfo=timezone.utc)

    r1 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet-v2-research",
        model_version="2.1.0",
        status="queued",
        created_at=now,
    )
    r2 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="clinical-bert-ner",
        model_version="1.0.4",
        status="running",
        created_at=now,
    )
    r3 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet-v2-research",
        model_version="2.1.0",
        status="completed",
        created_at=now,
    )
    r4 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="ecg-arrhythmia-cnn",
        model_version="0.9.1",
        status="failed",
        created_at=now,
    )
    r5 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet-v2-research",
        model_version="2.1.0",
        status="abstained",
        created_at=now,
    )

    db_session.add_all([r1, r2, r3, r4, r5])
    db_session.commit()

    summary = repo.get_analysis_summary()
    assert summary.total_runs == 5
    assert summary.by_status.queued == 1
    assert summary.by_status.running == 1
    assert summary.by_status.completed == 1
    assert summary.by_status.failed == 1
    assert summary.by_status.abstained == 1
    assert summary.active_models_observed == [
        "chexnet-v2-research",
        "clinical-bert-ner",
        "ecg-arrhythmia-cnn",
    ]


def test_pending_review_candidates_filtering(
    db_session: Session, repo: DashboardRepository, sample_patient: Patient
):
    """Verify only unreviewed completed/abstained runs appear in review queue."""
    t_early = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    t_late = datetime(2026, 1, 15, 14, 0, tzinfo=timezone.utc)

    # Candidate 1: completed, unreviewed
    r1 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet-v2-research",
        model_version="2.1.0",
        status="completed",
        created_at=t_early,
    )
    # Candidate 2: abstained, unreviewed (newer)
    r2 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="clinical-bert-ner",
        model_version="1.0.4",
        status="abstained",
        created_at=t_late,
    )
    # Excluded 1: running
    r3 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet-v2-research",
        model_version="2.1.0",
        status="running",
        created_at=t_late,
    )
    # Excluded 2: completed, but already formally reviewed via AuditEvent
    r4 = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet-v2-research",
        model_version="2.1.0",
        status="completed",
        created_at=t_early,
    )
    db_session.add_all([r1, r2, r3, r4])
    db_session.flush()

    audit_reviewed = AuditEvent(
        id=uuid.uuid4(),
        event_type="clinical_review",
        action="update",
        resource_type="analysis_run",
        resource_id=str(r4.id),
        created_at=t_late,
    )
    db_session.add(audit_reviewed)
    db_session.commit()

    queue = repo.get_pending_review_queue(limit=5)
    assert queue.pending_count == 2
    assert len(queue.items) == 2
    # Verify newest first ordering
    assert queue.items[0].run_id == r2.id
    assert queue.items[0].abstained is True
    assert queue.items[1].run_id == r1.id
    assert queue.items[1].abstained is False


def test_recent_activity_summary(
    db_session: Session, repo: DashboardRepository, sample_user: User
):
    """Verify recent operational activity aggregation and chronological ordering."""
    t1 = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 1, 6, 9, 30, tzinfo=timezone.utc)
    t3 = datetime(2026, 1, 7, 11, 15, tzinfo=timezone.utc)

    a1 = AuditEvent(
        id=uuid.uuid4(),
        actor_id=sample_user.id,
        event_type="patient.created",
        action="create",
        resource_type="patient",
        resource_id="PAT-001",
        description="patient registered",
        event_metadata={"status": "registered"},
        created_at=t1,
    )
    a2 = AuditEvent(
        id=uuid.uuid4(),
        actor_id=sample_user.id,
        event_type="analysis.completed",
        action="execute",
        resource_type="analysis_run",
        resource_id="RUN-002",
        description="analysis completed",
        event_metadata={"model": "chexnet-v2-research"},
        created_at=t2,
    )
    a3 = AuditEvent(
        id=uuid.uuid4(),
        actor_id=sample_user.id,
        event_type="user.login",
        action="read",
        resource_type="user",
        resource_id=str(sample_user.id),
        description="user login",
        event_metadata={"ip": "127.0.0.1"},
        created_at=t3,
    )
    db_session.add_all([a1, a2, a3])
    db_session.commit()

    summary = repo.get_recent_activity_summary(limit=2)
    assert summary.total_events == 3
    assert len(summary.activities) == 2
    # Most recent first
    assert summary.activities[0].event_type == "user.login"
    assert summary.activities[1].event_type == "analysis.completed"
    assert summary.activities[0].description == "user login"


def test_date_range_filtering(
    db_session: Session, repo: DashboardRepository, sample_patient: Patient
):
    """Verify aggregation queries respect UTC date range boundaries."""
    t_dec = datetime(2025, 12, 25, 12, 0, tzinfo=timezone.utc)
    t_jan = datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc)
    t_feb = datetime(2026, 2, 5, 12, 0, tzinfo=timezone.utc)

    # Encounters
    e_old = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="ambulatory",
        status="completed",
        start_time=t_dec,
    )
    e_mid = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="ambulatory",
        status="completed",
        start_time=t_jan,
    )
    e_future = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="ambulatory",
        status="completed",
        start_time=t_feb,
    )
    # Analysis runs
    r_old = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet",
        model_version="1",
        status="completed",
        created_at=t_dec,
    )
    r_mid = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet",
        model_version="1",
        status="completed",
        created_at=t_jan,
    )
    r_future = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet",
        model_version="1",
        status="completed",
        created_at=t_feb,
    )

    db_session.add_all([e_old, e_mid, e_future, r_old, r_mid, r_future])
    db_session.commit()

    # Filter to January 2026 only
    start_d = date(2026, 1, 1)
    end_d = date(2026, 1, 31)

    enc_summary = repo.get_encounter_summary(start_date=start_d, end_date=end_d)
    assert enc_summary.total_encounters == 1
    assert enc_summary.completed == 1

    run_summary = repo.get_analysis_summary(start_date=start_d, end_date=end_d)
    assert run_summary.total_runs == 1
    assert run_summary.by_status.completed == 1

    review_summary = repo.get_pending_review_queue(start_date=start_d, end_date=end_d)
    assert review_summary.pending_count == 1
    assert review_summary.items[0].run_id == r_mid.id


def test_status_filtering(
    db_session: Session, repo: DashboardRepository, sample_patient: Patient
):
    """Verify status filter isolates requested analysis lifecycle state."""
    now = datetime(2026, 1, 20, 12, 0, tzinfo=timezone.utc)

    r_comp = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="chexnet",
        model_version="1",
        status="completed",
        created_at=now,
    )
    r_run = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        model_name="bert",
        model_version="1",
        status="running",
        created_at=now,
    )

    db_session.add_all([r_comp, r_run])
    db_session.commit()

    # Filter by "completed"
    analysis_comp = repo.get_analysis_summary(status_filter="completed")
    assert analysis_comp.total_runs == 1
    assert analysis_comp.by_status.completed == 1
    assert analysis_comp.by_status.running == 0

    review_comp = repo.get_pending_review_queue(status_filter="completed")
    assert review_comp.pending_count == 1
    assert review_comp.items[0].run_id == r_comp.id

    # Filter by "running" -> pending reviews must be empty since running runs are not review candidates
    review_run = repo.get_pending_review_queue(status_filter="running")
    assert review_run.pending_count == 0
    assert review_run.items == []
