"""Arogya AI - Healthcare Data Model Tests.

Module 3, Phase 3.3: Initial Entities & Relational Data Models.
Tests entity mappings, primary/foreign keys, uniqueness constraints,
relationships, deletion cascades, and integrity rules on an isolated SQLite engine.
"""

from datetime import date, datetime, timezone
import uuid

import pytest
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

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
    user_roles,
)
from backend.app.db.session import create_db_engine


@pytest.fixture
def test_db_engine() -> Engine:
    """Provide an isolated in-memory SQLite engine with foreign key enforcement enabled."""
    engine = create_db_engine("sqlite:///:memory:")

    # SQLite does not enforce foreign keys by default; enable PRAGMA foreign_keys on each checkout
    @event.listens_for(engine, "connect")
    def enable_sqlite_fk(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Create all entity tables only within the test fixture
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_db_engine: Engine) -> Session:
    """Provide an active session bound to the test database engine."""
    factory = sessionmaker(bind=test_db_engine, autoflush=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. Metadata & Table Registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_all_eight_entity_tables_registered_in_metadata():
    """Verify all 8 expected domain entity tables plus user_roles are registered in Base.metadata."""
    expected_tables = {
        "users",
        "roles",
        "user_roles",
        "patients",
        "encounters",
        "observations",
        "uploaded_assets",
        "analysis_runs",
        "audit_events",
    }
    actual_tables = set(Base.metadata.tables.keys())
    assert expected_tables.issubset(actual_tables)
    assert len(expected_tables) == 9


# ---------------------------------------------------------------------------
# 2. Primary Keys & Foreign Keys Structure
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_primary_keys_and_foreign_keys_definitions():
    """Verify primary and foreign key constraints on all domain entities."""
    # User & Role PKs
    assert [col.name for col in Base.metadata.tables["users"].primary_key.columns] == ["id"]
    assert [col.name for col in Base.metadata.tables["roles"].primary_key.columns] == ["id"]

    # user_roles composite PK
    user_roles_pk = [col.name for col in Base.metadata.tables["user_roles"].primary_key.columns]
    assert sorted(user_roles_pk) == ["role_id", "user_id"]

    # Patient PK
    assert [col.name for col in Base.metadata.tables["patients"].primary_key.columns] == ["id"]

    # Encounter FK to Patient
    encounter_fks = Base.metadata.tables["encounters"].foreign_keys
    assert any(fk.target_fullname == "patients.id" for fk in encounter_fks)

    # Observation FKs to Encounter and Patient
    obs_fks = {fk.target_fullname for fk in Base.metadata.tables["observations"].foreign_keys}
    assert "encounters.id" in obs_fks
    assert "patients.id" in obs_fks

    # UploadedAsset FKs
    asset_fks = {fk.target_fullname for fk in Base.metadata.tables["uploaded_assets"].foreign_keys}
    assert "patients.id" in asset_fks
    assert "encounters.id" in asset_fks

    # AnalysisRun FKs
    run_fks = {fk.target_fullname for fk in Base.metadata.tables["analysis_runs"].foreign_keys}
    assert "patients.id" in run_fks
    assert "encounters.id" in run_fks
    assert "uploaded_assets.id" in run_fks

    # AuditEvent FK to User
    audit_fks = {fk.target_fullname for fk in Base.metadata.tables["audit_events"].foreign_keys}
    assert "users.id" in audit_fks


# ---------------------------------------------------------------------------
# 3. Uniqueness Constraints
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_uniqueness_constraints(db_session: Session):
    """Verify uniqueness constraints on username, email, role name, MRN, and asset path."""
    # 1. Duplicate role name
    r1 = Role(name="researcher")
    db_session.add(r1)
    db_session.commit()

    r2 = Role(name="researcher")
    db_session.add(r2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 2. Duplicate username
    u1 = User(username="dr_smith", email="smith@hospital.org", full_name="Dr. Smith")
    db_session.add(u1)
    db_session.commit()

    u2 = User(username="dr_smith", email="other@hospital.org", full_name="Other Smith")
    db_session.add(u2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 3. Duplicate email
    u3 = User(username="different_handle", email="smith@hospital.org", full_name="Diff Smith")
    db_session.add(u3)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 4. Duplicate Patient MRN Pseudonym
    p1 = Patient(mrn_pseudonym="SYNTH-001")
    db_session.add(p1)
    db_session.commit()

    p2 = Patient(mrn_pseudonym="SYNTH-001")
    db_session.add(p2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # 5. Duplicate UploadedAsset storage_path
    a1 = UploadedAsset(
        patient_id=p1.id,
        original_filename="scan.png",
        media_type="image/png",
        file_size_bytes=1024,
        storage_path="assets/p1/scan.png",
        checksum_sha256="abc123hash",
    )
    db_session.add(a1)
    db_session.commit()

    a2 = UploadedAsset(
        patient_id=p1.id,
        original_filename="scan2.png",
        media_type="image/png",
        file_size_bytes=2048,
        storage_path="assets/p1/scan.png",  # Same storage path
        checksum_sha256="def456hash",
    )
    db_session.add(a2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 4. User & Role Many-to-Many Association
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_user_role_many_to_many_association(db_session: Session):
    """Verify many-to-many relationship between Users and Roles via user_roles."""
    role_admin = Role(name="administrator", description="System admin")
    role_doc = Role(name="clinician", description="Reviewing clinician")
    db_session.add_all([role_admin, role_doc])
    db_session.commit()

    user = User(
        username="clinician_admin",
        email="chief@hospital.org",
        full_name="Chief Medical Officer",
        roles=[role_admin, role_doc],
    )
    db_session.add(user)
    db_session.commit()

    # Query from database to verify association persisted
    loaded_user = db_session.get(User, user.id)
    assert loaded_user is not None
    assert len(loaded_user.roles) == 2
    role_names = {r.name for r in loaded_user.roles}
    assert role_names == {"administrator", "clinician"}

    # Role back-populates to user
    loaded_admin_role = db_session.get(Role, role_admin.id)
    assert loaded_admin_role is not None
    assert any(u.id == user.id for u in loaded_admin_role.users)


# ---------------------------------------------------------------------------
# 5. Patient -> Encounter -> Observation Hierarchy
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_patient_encounter_observation_hierarchy(db_session: Session):
    """Verify relational hierarchy from Patient to Encounter and Observation."""
    patient = Patient(
        mrn_pseudonym="SYNTH-CARDIO-01",
        birth_date=date(1980, 5, 12),
        biological_sex="female",
        is_synthetic=True,
    )
    db_session.add(patient)
    db_session.commit()

    encounter = Encounter(
        patient_id=patient.id,
        encounter_type="ambulatory",
        status="completed",
        start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 25, 10, 30, tzinfo=timezone.utc),
    )
    db_session.add(encounter)
    db_session.commit()

    # Quantitative vital observation (heart rate)
    obs_hr = Observation(
        encounter_id=encounter.id,
        patient_id=patient.id,
        code="8867-4",
        display_name="Heart Rate",
        numeric_value=72.0,
        text_value=None,
        unit="bpm",
        observed_at=datetime(2026, 10, 25, 10, 5, tzinfo=timezone.utc),
        source_metadata={"sensor": "pulse_oximeter", "synthetic": True},
    )

    # Qualitative clinical observation (symptom severity)
    obs_symptom = Observation(
        encounter_id=encounter.id,
        patient_id=patient.id,
        code="cough_presence",
        display_name="Cough Symptom",
        numeric_value=None,
        text_value="mild_intermittent",
        unit=None,
        observed_at=datetime(2026, 10, 25, 10, 5, tzinfo=timezone.utc),
    )
    db_session.add_all([obs_hr, obs_symptom])
    db_session.commit()

    # Verify bidirectional navigation
    loaded_patient = db_session.get(Patient, patient.id)
    assert loaded_patient is not None
    assert len(loaded_patient.encounters) == 1
    assert len(loaded_patient.observations) == 2

    loaded_encounter = db_session.get(Encounter, encounter.id)
    assert loaded_encounter is not None
    assert loaded_encounter.patient.id == patient.id
    assert len(loaded_encounter.observations) == 2

    # Verify numeric and text representations
    loaded_obs = {o.code: o for o in loaded_encounter.observations}
    assert loaded_obs["8867-4"].numeric_value == 72.0
    assert loaded_obs["8867-4"].text_value is None
    assert loaded_obs["8867-4"].unit == "bpm"

    assert loaded_obs["cough_presence"].numeric_value is None
    assert loaded_obs["cough_presence"].text_value == "mild_intermittent"


# ---------------------------------------------------------------------------
# 6. Uploaded Asset & Analysis Run Relationships
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_uploaded_asset_and_analysis_run_relationships(db_session: Session):
    """Verify UploadedAsset and AnalysisRun relationships and segregated outputs."""
    patient = Patient(mrn_pseudonym="SYNTH-XRAY-02")
    db_session.add(patient)
    db_session.commit()

    encounter = Encounter(
        patient_id=patient.id,
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(encounter)
    db_session.commit()

    asset = UploadedAsset(
        patient_id=patient.id,
        encounter_id=encounter.id,
        original_filename="chest_pa_view.png",
        media_type="image/png",
        file_size_bytes=4194304,
        storage_path="imaging/2026/10/chest_pa_view.png",
        checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    db_session.add(asset)
    db_session.commit()

    run = AnalysisRun(
        patient_id=patient.id,
        encounter_id=encounter.id,
        asset_id=asset.id,
        model_name="cxr_densenet121_baseline",
        model_version="0.1.0-alpha",
        status="completed",
        parameters={"confidence_threshold": 0.5, "device": "cpu"},
        results_summary={
            "pneumonia_prob": 0.12,
            "normal_prob": 0.88,
            "uncertainty_score": 0.05,
            "abstention_triggered": False,
        },
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()

    # Verify bidirectional navigation
    loaded_asset = db_session.get(UploadedAsset, asset.id)
    assert loaded_asset is not None
    assert len(loaded_asset.analysis_runs) == 1
    assert loaded_asset.analysis_runs[0].id == run.id

    loaded_run = db_session.get(AnalysisRun, run.id)
    assert loaded_run is not None
    assert loaded_run.asset is not None
    assert loaded_run.asset.id == asset.id
    assert loaded_run.patient.id == patient.id
    assert loaded_run.encounter is not None
    assert loaded_run.encounter.id == encounter.id

    # Verify model outputs are structured and segregated
    assert loaded_run.results_summary["pneumonia_prob"] == 0.12
    assert loaded_run.results_summary["abstention_triggered"] is False


# ---------------------------------------------------------------------------
# 7. Audit Event Traceability & Privacy Safety
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_audit_event_logging_and_actor_reference(db_session: Session):
    """Verify AuditEvent traces actions, links optional actor, and preserves privacy."""
    user = User(
        username="audited_user",
        email="audit@hospital.org",
        full_name="Audit Test User",
    )
    db_session.add(user)
    db_session.commit()

    # User-initiated audit event
    user_event = AuditEvent(
        event_type="case.reviewed",
        actor_id=user.id,
        action="update",
        resource_type="encounter",
        resource_id=str(uuid.uuid4()),
        description="Clinician marked encounter review completed",
        ip_address="127.0.0.1",
        event_metadata={"request_id": "req-9876-abcd", "duration_ms": 42},
    )

    # Autonomous / system event without actor
    system_event = AuditEvent(
        event_type="system.backup",
        actor_id=None,
        action="execute",
        resource_type="system",
        resource_id="backup_job_1",
        description="Automated synthetic database snapshot",
        ip_address=None,
        event_metadata={"snapshot_type": "full", "bytes": 1048576},
    )
    db_session.add_all([user_event, system_event])
    db_session.commit()

    # Verify actor linkage
    loaded_event = db_session.get(AuditEvent, user_event.id)
    assert loaded_event is not None
    assert loaded_event.actor is not None
    assert loaded_event.actor.username == "audited_user"
    assert loaded_event.event_metadata["request_id"] == "req-9876-abcd"

    loaded_sys_event = db_session.get(AuditEvent, system_event.id)
    assert loaded_sys_event is not None
    assert loaded_sys_event.actor_id is None
    assert loaded_sys_event.actor is None


# ---------------------------------------------------------------------------
# 8. Timestamps and Nullable Fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_timestamps_and_nullable_field_defaults(db_session: Session):
    """Verify timezone-aware timestamps and nullable field behavior across entities."""
    patient = Patient(mrn_pseudonym="SYNTH-TIME-01")
    db_session.add(patient)
    db_session.commit()

    # created_at is automatically populated and timezone-aware
    assert patient.created_at is not None
    assert patient.created_at.tzinfo is not None
    assert patient.updated_at is not None

    # Nullable fields on Patient default to None
    assert patient.birth_date is None
    assert patient.biological_sex is None

    # Non-nullable field validation on insert: encounter without start_time fails
    bad_encounter = Encounter(
        patient_id=patient.id,
        # Missing start_time
    )
    db_session.add(bad_encounter)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ---------------------------------------------------------------------------
# 9. Foreign Key Enforcement & Deletion Policies (RESTRICT & SET NULL)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_foreign_key_rejection_of_invalid_references(db_session: Session):
    """Verify invalid foreign keys are rejected when foreign key enforcement is active."""
    non_existent_patient_id = uuid.uuid4()
    bad_encounter = Encounter(
        patient_id=non_existent_patient_id,
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(bad_encounter)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.unit
def test_restrict_deletion_policy_protects_clinical_history(db_session: Session):
    """Verify RESTRICT deletion policy prevents deleting patients with active encounters."""
    patient = Patient(mrn_pseudonym="SYNTH-RESTRICT-01")
    db_session.add(patient)
    db_session.commit()

    encounter = Encounter(
        patient_id=patient.id,
        start_time=datetime.now(timezone.utc),
    )
    db_session.add(encounter)
    db_session.commit()

    # Attempting to delete patient while encounter exists must fail with IntegrityError
    db_session.delete(patient)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # Deleting patient with active observations must also be restricted
    obs = Observation(
        encounter_id=encounter.id,
        patient_id=patient.id,
        code="test_code",
        display_name="Test Observation",
        numeric_value=1.0,
        observed_at=datetime.now(timezone.utc),
    )
    db_session.add(obs)
    db_session.commit()

    # Attempting to delete encounter while observation exists must fail
    db_session.delete(encounter)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


@pytest.mark.unit
def test_set_null_deletion_policy_on_audit_and_assets(db_session: Session):
    """Verify SET NULL deletion behavior on audit actor and asset runs."""
    # 1. User deletion preserves AuditEvent with actor_id=NULL
    user = User(username="temp_user", email="temp@hospital.org", full_name="Temp User")
    db_session.add(user)
    db_session.commit()

    event_obj = AuditEvent(
        event_type="session.start",
        actor_id=user.id,
        action="execute",
    )
    db_session.add(event_obj)
    db_session.commit()

    event_id = event_obj.id
    db_session.delete(user)
    db_session.commit()

    preserved_event = db_session.get(AuditEvent, event_id)
    assert preserved_event is not None
    assert preserved_event.actor_id is None

    # 2. Asset deletion sets AnalysisRun.asset_id to NULL
    patient = Patient(mrn_pseudonym="SYNTH-ASSET-DEL-01")
    db_session.add(patient)
    db_session.commit()

    asset = UploadedAsset(
        patient_id=patient.id,
        original_filename="image_to_delete.png",
        media_type="image/png",
        file_size_bytes=100,
        storage_path="path/to/image_to_delete.png",
        checksum_sha256="hash12345",
    )
    db_session.add(asset)
    db_session.commit()

    run = AnalysisRun(
        patient_id=patient.id,
        asset_id=asset.id,
        model_name="test_model",
        model_version="1.0",
        status="completed",
    )
    db_session.add(run)
    db_session.commit()

    run_id = run.id
    db_session.delete(asset)
    db_session.commit()

    preserved_run = db_session.get(AnalysisRun, run_id)
    assert preserved_run is not None
    assert preserved_run.asset_id is None
