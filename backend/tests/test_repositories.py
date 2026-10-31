"""Arogya AI — Data Access Repositories Unit Tests.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Verifies CRUD operations, bounded pagination clamping, foreign key enforcement,
uniqueness constraints, and eager loading across all domain repositories.
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.models import (
    AnalysisRun,
    AuditEvent,
    Encounter,
    Observation,
    Patient,
    Role,
    UploadedAsset,
    User,
)
from backend.app.repositories.analysis import AnalysisRepository
from backend.app.repositories.asset import AssetRepository
from backend.app.repositories.audit import AuditRepository
from backend.app.repositories.base import BaseRepository
from backend.app.repositories.encounter import EncounterRepository
from backend.app.repositories.observation import ObservationRepository
from backend.app.repositories.patient import PatientRepository
from backend.app.repositories.user import RoleRepository, UserRepository


@pytest.fixture
def repo_session() -> Session:
    """Fixture providing an isolated in-memory SQLite session with foreign keys enforced."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable SQLite foreign key constraint enforcement
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
        engine.dispose()


def test_base_repository_pagination_sanitization() -> None:
    """Verify that pagination limit and offset are correctly sanitized and clamped."""
    # Negative values clamped to safe minimums
    limit, offset = BaseRepository._sanitize_pagination(limit=-10, offset=-5)
    assert limit == 1
    assert offset == 0

    # Values exceeding ceiling clamped to max_limit
    limit, offset = BaseRepository._sanitize_pagination(limit=1000, offset=50, max_limit=500)
    assert limit == 500
    assert offset == 50

    # Standard valid values preserved
    limit, offset = BaseRepository._sanitize_pagination(limit=25, offset=10)
    assert limit == 25
    assert offset == 10


def test_role_repository_crud(repo_session: Session) -> None:
    """Verify RoleRepository create, retrieval, pagination, and missing-record handling."""
    repo = RoleRepository(repo_session)

    # 1. Create role
    role = repo.create(name="Clinician", description="Licensed clinical provider")
    assert role.id is not None
    assert role.name == "clinician"  # Normalized to lowercase
    assert role.description == "Licensed clinical provider"

    # 2. Retrieve by ID
    fetched_by_id = repo.get_by_id(role.id)
    assert fetched_by_id is not None
    assert fetched_by_id.id == role.id

    # 3. Retrieve by name
    fetched_by_name = repo.get_by_name("clinician")
    assert fetched_by_name is not None
    assert fetched_by_name.id == role.id

    # 4. Missing record returns None
    assert repo.get_by_id(uuid.uuid4()) is None
    assert repo.get_by_name("non_existent_role") is None

    # 5. List roles
    repo.create(name="Administrator", description="System admin")
    roles = repo.list_roles(limit=10, offset=0)
    assert len(roles) == 2
    assert [r.name for r in roles] == ["administrator", "clinician"]  # Alphabetical order


def test_user_repository_crud_and_role_associations(repo_session: Session) -> None:
    """Verify UserRepository CRUD operations, eager-loaded roles, and role link/unlink."""
    role_repo = RoleRepository(repo_session)
    user_repo = UserRepository(repo_session)

    clinician_role = role_repo.create("clinician")
    admin_role = role_repo.create("administrator")

    # 1. Create user with role
    user = user_repo.create(
        username="dr_sharma",
        email="sharma@hospital.org",
        full_name="Dr. Sharma",
        hashed_password="mock_hash_string",
        is_active=True,
        roles=[clinician_role],
    )
    assert user.id is not None
    assert len(user.roles) == 1
    assert user.roles[0].name == "clinician"

    # 2. Query by ID, username, email
    assert user_repo.get_by_id(user.id) is not None
    assert user_repo.get_by_username("dr_sharma") is not None
    assert user_repo.get_by_email("sharma@hospital.org") is not None
    assert user_repo.get_by_username("non_existent") is None

    # 3. Assign second role
    user_repo.assign_role(user, admin_role)
    assert len(user.roles) == 2

    # 4. Remove role
    user_repo.remove_role(user, clinician_role)
    assert len(user.roles) == 1
    assert user.roles[0].name == "administrator"

    # 5. Update user fields
    user_repo.update(user, full_name="Dr. S. Sharma", is_active=False)
    assert user.full_name == "Dr. S. Sharma"
    assert user.is_active is False

    # 6. Listing and counting with filters
    assert user_repo.count_users(is_active=False) == 1
    assert user_repo.count_users(is_active=True) == 0
    users = user_repo.list_users(limit=10, is_active=False)
    assert len(users) == 1


def test_patient_repository_crud_and_mrn(repo_session: Session) -> None:
    """Verify PatientRepository CRUD operations, pseudonymous MRN lookup, and synthetic filters."""
    repo = PatientRepository(repo_session)

    # 1. Create synthetic patient
    patient = repo.create(
        mrn_pseudonym="SYNTH-PAT-0001",
        birth_date=date(1985, 6, 15),
        biological_sex="female",
        is_synthetic=True,
    )
    assert patient.id is not None
    assert patient.mrn_pseudonym == "SYNTH-PAT-0001"
    assert patient.is_synthetic is True

    # 2. Retrieval by ID and MRN
    assert repo.get_by_id(patient.id) is not None
    assert repo.get_by_mrn("SYNTH-PAT-0001") is not None
    assert repo.get_by_mrn("NON-EXISTENT") is None

    # 3. Update fields
    repo.update(patient, biological_sex="other", birth_date=date(1985, 6, 16))
    assert patient.biological_sex == "other"
    assert patient.birth_date == date(1985, 6, 16)

    # 4. List and count
    repo.create("SYNTH-PAT-0002", is_synthetic=False)
    assert repo.count_patients(is_synthetic=True) == 1
    assert repo.count_patients(is_synthetic=False) == 1
    assert len(repo.list_patients(limit=10)) == 2


def test_encounter_repository_crud(repo_session: Session) -> None:
    """Verify EncounterRepository create, update, and patient-scoped queries."""
    patient_repo = PatientRepository(repo_session)
    encounter_repo = EncounterRepository(repo_session)

    patient = patient_repo.create("SYNTH-PAT-0001")
    start_dt = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)

    # 1. Create encounter
    encounter = encounter_repo.create(
        patient_id=patient.id,
        start_time=start_dt,
        encounter_type="ambulatory",
        status="in_progress",
    )
    assert encounter.id is not None
    assert encounter.patient_id == patient.id
    assert encounter.status == "in_progress"

    # 2. Update status and end time
    end_dt = datetime(2026, 10, 25, 11, 0, tzinfo=timezone.utc)
    encounter_repo.update(encounter, status="completed", end_time=end_dt)
    assert encounter.status == "completed"
    assert encounter.end_time == end_dt

    # 3. List and count encounters by patient
    encounters = encounter_repo.list_by_patient(patient.id, status="completed")
    assert len(encounters) == 1
    assert encounter_repo.count_by_patient(patient.id, status="completed") == 1
    assert encounter_repo.count_by_patient(patient.id, status="in_progress") == 0


def test_observation_repository_crud(repo_session: Session) -> None:
    """Verify ObservationRepository numeric vs text value segregation and filtering."""
    patient_repo = PatientRepository(repo_session)
    encounter_repo = EncounterRepository(repo_session)
    obs_repo = ObservationRepository(repo_session)

    patient = patient_repo.create("SYNTH-PAT-0001")
    encounter = encounter_repo.create(
        patient_id=patient.id,
        start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
    )
    obs_time = datetime(2026, 10, 25, 10, 15, tzinfo=timezone.utc)

    # 1. Create quantitative numeric observation
    obs_num = obs_repo.create(
        encounter_id=encounter.id,
        patient_id=patient.id,
        code="8867-4",
        display_name="Heart Rate",
        observed_at=obs_time,
        numeric_value=72.0,
        unit="bpm",
    )
    assert obs_num.id is not None
    assert obs_num.numeric_value == 72.0
    assert obs_num.text_value is None

    # 2. Create qualitative text observation
    obs_text = obs_repo.create(
        encounter_id=encounter.id,
        patient_id=patient.id,
        code="49727-2",
        display_name="Cough Assessment",
        observed_at=obs_time,
        text_value="Mild intermittent dry cough",
    )
    assert obs_text.id is not None
    assert obs_text.text_value == "Mild intermittent dry cough"
    assert obs_text.numeric_value is None

    # 3. List by encounter
    by_enc = obs_repo.list_by_encounter(encounter.id)
    assert len(by_enc) == 2

    # 4. List and count by patient and code filter
    by_code = obs_repo.list_by_patient(patient.id, code="8867-4")
    assert len(by_code) == 1
    assert by_code[0].code == "8867-4"
    assert obs_repo.count_by_patient(patient.id) == 2


def test_asset_repository_crud(repo_session: Session) -> None:
    """Verify AssetRepository creation, storage path uniqueness lookup, and patient queries."""
    patient_repo = PatientRepository(repo_session)
    asset_repo = AssetRepository(repo_session)

    patient = patient_repo.create("SYNTH-PAT-0001")
    storage_path = "assets/2026/10/cxr_phantom_001.png"

    # 1. Create asset
    asset = asset_repo.create(
        patient_id=patient.id,
        original_filename="cxr_phantom_001.png",
        media_type="image/png",
        file_size_bytes=2048576,
        storage_path=storage_path,
        checksum_sha256="a" * 64,
    )
    assert asset.id is not None
    assert asset.storage_path == storage_path

    # 2. Retrieve by storage path
    fetched = asset_repo.get_by_storage_path(storage_path)
    assert fetched is not None
    assert fetched.id == asset.id
    assert asset_repo.get_by_storage_path("non/existent") is None

    # 3. List and count by patient
    assets = asset_repo.list_by_patient(patient.id)
    assert len(assets) == 1
    assert asset_repo.count_by_patient(patient.id) == 1


def test_analysis_repository_crud(repo_session: Session) -> None:
    """Verify AnalysisRepository creation, status update with results, and queries."""
    patient_repo = PatientRepository(repo_session)
    encounter_repo = EncounterRepository(repo_session)
    analysis_repo = AnalysisRepository(repo_session)

    patient = patient_repo.create("SYNTH-PAT-0001")
    encounter = encounter_repo.create(
        patient_id=patient.id,
        start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
    )

    # 1. Create analysis run
    run = analysis_repo.create(
        patient_id=patient.id,
        encounter_id=encounter.id,
        model_name="cxr_densenet121",
        model_version="v1.0.0",
        status="queued",
        parameters={"threshold": 0.5},
    )
    assert run.id is not None
    assert run.status == "queued"

    # 2. Update status and results
    now = datetime(2026, 10, 25, 10, 5, tzinfo=timezone.utc)
    analysis_repo.update_status(
        run=run,
        status="completed",
        results_summary={"risk_score": 0.15, "finding": "clear"},
        completed_at=now,
    )
    assert run.status == "completed"
    assert run.results_summary["risk_score"] == 0.15
    assert run.completed_at == now

    # 3. List by patient and encounter
    assert len(analysis_repo.list_by_patient(patient.id, status="completed")) == 1
    assert len(analysis_repo.list_by_encounter(encounter.id)) == 1
    assert analysis_repo.count_by_patient(patient.id, status="completed") == 1


def test_audit_repository_immutability_and_filters(repo_session: Session) -> None:
    """Verify AuditRepository creation, filtering, and absence of mutation operations."""
    repo = AuditRepository(repo_session)

    # Confirm design rule: no update or delete methods exist
    assert not hasattr(repo, "update")
    assert not hasattr(repo, "delete")

    # Create audit event
    event = repo.create(
        event_type="patient.created",
        action="create",
        resource_type="patient",
        resource_id="12345",
        description="Created patient cohort record",
        event_metadata={"test": True},
    )
    assert event.id is not None
    assert event.event_type == "patient.created"

    # Query with filters
    events = repo.list_events(resource_type="patient", action="create")
    assert len(events) == 1
    assert repo.count_events(resource_type="patient") == 1
    assert repo.count_events(resource_type="encounter") == 0


def test_repository_foreign_key_violations_enforced(repo_session: Session) -> None:
    """Verify that foreign key constraints raise IntegrityError on invalid parent keys."""
    encounter_repo = EncounterRepository(repo_session)
    non_existent_patient_id = uuid.uuid4()

    # Attempt to insert encounter with non-existent patient_id
    with pytest.raises(IntegrityError):
        encounter_repo.create(
            patient_id=non_existent_patient_id,
            start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
        )
        repo_session.flush()
