"""Arogya AI — Domain Services Unit Tests.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Verifies cross-entity consistency, transaction rollback boundaries, MRN mapping,
audit logging, sensitive metadata sanitization, and synthetic data preservation.
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from sqlalchemy import create_engine, event, select
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
from backend.app.schemas.analysis import AnalysisRunCreate
from backend.app.schemas.asset import AssetMetadataCreate
from backend.app.schemas.encounter import EncounterCreate, EncounterUpdate
from backend.app.schemas.observation import ObservationCreate
from backend.app.schemas.patient import PatientCreate, PatientUpdate
from backend.app.schemas.user import UserCreate, UserUpdate
from backend.app.services.audit import AuditService, sanitize_audit_metadata
from backend.app.services.clinical import ClinicalService
from backend.app.services.exceptions import (
    ConsistencyError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from backend.app.services.user import UserService


@pytest.fixture
def service_session() -> Session:
    """Fixture providing an isolated in-memory SQLite session with foreign keys enforced."""
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
        engine.dispose()


def test_user_service_create_and_unique_validation(service_session: Session) -> None:
    """Verify UserService user creation, role assignment, and uniqueness validation."""
    service = UserService(service_session)
    service.create_role(name="clinician", description="Clinical provider")

    # 1. Create valid user with role
    user_data = UserCreate(
        username="dr_patel",
        email="patel@hospital.org",
        full_name="Dr. Patel",
        password="ValidPassword123",
    )
    user = service.create_user(
        data=user_data,
        hashed_password="hashed_patel_pw",
        role_names=["clinician"],
    )
    assert user.id is not None
    assert user.username == "dr_patel"
    assert len(user.roles) == 1
    assert user.roles[0].name == "clinician"

    # 2. Duplicate username raises DuplicateEntityError
    with pytest.raises(DuplicateEntityError) as exc_info:
        service.create_user(
            data=UserCreate(
                username="dr_patel",
                email="other_email@hospital.org",
                full_name="Other Patel",
                password="ValidPassword123",
            )
        )
    assert "username" in str(exc_info.value)

    # 3. Duplicate email raises DuplicateEntityError
    with pytest.raises(DuplicateEntityError) as exc_info:
        service.create_user(
            data=UserCreate(
                username="unique_handle",
                email="patel@hospital.org",
                full_name="Unique User",
                password="ValidPassword123",
            )
        )
    assert "email" in str(exc_info.value)

    # 4. Non-existent role raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError) as exc_info:
        service.create_user(
            data=UserCreate(
                username="dr_nobody",
                email="nobody@hospital.org",
                full_name="Dr. Nobody",
                password="ValidPassword123",
            ),
            role_names=["non_existent_role_name"],
        )
    assert "Role" in str(exc_info.value)


def test_user_service_update_and_role_management(service_session: Session) -> None:
    """Verify UserService update operations and role assignment/removal."""
    service = UserService(service_session)
    service.create_role("clinician")
    service.create_role("researcher")

    user = service.create_user(
        data=UserCreate(
            username="analyst_1",
            email="analyst@hospital.org",
            full_name="Data Analyst",
            password="ValidPassword123",
        ),
        role_names=["researcher"],
    )

    # Update full name
    updated = service.update_user(user.id, UserUpdate(full_name="Senior Data Analyst"))
    assert updated.full_name == "Senior Data Analyst"

    # Assign additional role
    service.assign_role(user.id, "clinician")
    assert len(user.roles) == 2

    # Remove role
    service.remove_role(user.id, "researcher")
    assert len(user.roles) == 1
    assert user.roles[0].name == "clinician"


def test_clinical_service_patient_creation_and_mrn_mapping(service_session: Session) -> None:
    """Verify Patient creation and explicit mapping between 'mrn' alias and 'mrn_pseudonym'."""
    service = ClinicalService(service_session)

    # 1. Create using mrn_pseudonym field directly
    p1 = service.create_patient(
        PatientCreate(
            mrn_pseudonym="SYNTH-PAT-0001",
            birth_date=date(1980, 1, 1),
            biological_sex="female",
            is_synthetic=True,
        )
    )
    assert p1.mrn_pseudonym == "SYNTH-PAT-0001"
    assert p1.is_synthetic is True

    # 2. Create using 'mrn' alias (via Pydantic AliasChoices)
    p2 = service.create_patient(
        PatientCreate.model_validate(
            {
                "mrn": "SYNTH-PAT-0002",
                "birth_date": date(1990, 5, 20),
                "biological_sex": "male",
                "is_synthetic": True,
            }
        )
    )
    assert p2.mrn_pseudonym == "SYNTH-PAT-0002"

    # 3. Querying by MRN works identically
    fetched_p1 = service.get_patient_by_mrn("SYNTH-PAT-0001")
    assert fetched_p1 is not None
    assert fetched_p1.id == p1.id

    fetched_p2 = service.get_patient_by_mrn("SYNTH-PAT-0002")
    assert fetched_p2 is not None
    assert fetched_p2.id == p2.id

    # 4. Duplicate MRN raises DuplicateEntityError
    with pytest.raises(DuplicateEntityError) as exc_info:
        service.create_patient(
            PatientCreate(
                mrn_pseudonym="SYNTH-PAT-0001",
                birth_date=date(1980, 1, 1),
            )
        )
    assert "mrn" in str(exc_info.value)


def test_clinical_service_encounter_consistency(service_session: Session) -> None:
    """Verify encounter creation requires an existing patient record."""
    service = ClinicalService(service_session)

    patient = service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-PAT-0001"))

    # Valid encounter creation
    encounter = service.create_encounter(
        EncounterCreate(
            patient_id=patient.id,
            start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
            encounter_type="ambulatory",
            status="in_progress",
        )
    )
    assert encounter.id is not None
    assert encounter.patient_id == patient.id

    # Encounter referencing non-existent patient raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError) as exc_info:
        service.create_encounter(
            EncounterCreate(
                patient_id=uuid.uuid4(),
                start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
            )
        )
    assert "Patient" in str(exc_info.value)


def test_clinical_service_observation_ownership_consistency(service_session: Session) -> None:
    """Verify observations enforce that encounter patient_id matches observation patient_id."""
    service = ClinicalService(service_session)

    pat_a = service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-PAT-000A"))
    pat_b = service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-PAT-000B"))

    enc_a = service.create_encounter(
        EncounterCreate(
            patient_id=pat_a.id,
            start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
        )
    )

    # 1. Consistent observation (patient_id matches encounter.patient_id)
    obs = service.create_observation(
        ObservationCreate(
            encounter_id=enc_a.id,
            patient_id=pat_a.id,
            code="8867-4",
            display_name="Heart Rate",
            observed_at=datetime(2026, 10, 25, 10, 15, tzinfo=timezone.utc),
            numeric_value=75.0,
            unit="bpm",
        )
    )
    assert obs.id is not None
    assert obs.encounter_id == enc_a.id
    assert obs.patient_id == pat_a.id

    # 2. Inconsistent observation (encounter belongs to Patient A, but observation cites Patient B)
    with pytest.raises(ConsistencyError) as exc_info:
        service.create_observation(
            ObservationCreate(
                encounter_id=enc_a.id,
                patient_id=pat_b.id,  # MISMATCH
                code="8867-4",
                display_name="Heart Rate",
                observed_at=datetime(2026, 10, 25, 10, 15, tzinfo=timezone.utc),
                numeric_value=75.0,
                unit="bpm",
            )
        )
    assert "does not match encounter patient_id" in str(exc_info.value)

    # 3. Non-existent encounter raises EntityNotFoundError
    with pytest.raises(EntityNotFoundError) as exc_info:
        service.create_observation(
            ObservationCreate(
                encounter_id=uuid.uuid4(),
                patient_id=pat_a.id,
                code="8867-4",
                display_name="Heart Rate",
                observed_at=datetime(2026, 10, 25, 10, 15, tzinfo=timezone.utc),
                numeric_value=75.0,
            )
        )
    assert "Encounter" in str(exc_info.value)


def test_clinical_service_asset_ownership_consistency(service_session: Session) -> None:
    """Verify uploaded asset metadata validates patient existence and encounter alignment."""
    service = ClinicalService(service_session)

    pat_a = service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-PAT-000A"))
    pat_b = service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-PAT-000B"))

    enc_a = service.create_encounter(
        EncounterCreate(
            patient_id=pat_a.id,
            start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
        )
    )

    # 1. Consistent asset
    asset = service.register_asset_metadata(
        data=AssetMetadataCreate(
            patient_id=pat_a.id,
            encounter_id=enc_a.id,
            original_filename="scan_01.png",
            media_type="image/png",
            file_size_bytes=1048576,
            checksum_sha256="b" * 64,
        ),
        storage_path="assets/scan_01.png",
    )
    assert asset.id is not None
    assert asset.patient_id == pat_a.id

    # 2. Inconsistent encounter (encounter belongs to Patient A, asset claims Patient B)
    with pytest.raises(ConsistencyError) as exc_info:
        service.register_asset_metadata(
            data=AssetMetadataCreate(
                patient_id=pat_b.id,  # Mismatch
                encounter_id=enc_a.id,
                original_filename="scan_02.png",
                media_type="image/png",
                file_size_bytes=1048576,
                checksum_sha256="c" * 64,
            ),
            storage_path="assets/scan_02.png",
        )
    assert "belongs to patient" in str(exc_info.value)

    # 3. Duplicate storage path raises DuplicateEntityError
    with pytest.raises(DuplicateEntityError) as exc_info:
        service.register_asset_metadata(
            data=AssetMetadataCreate(
                patient_id=pat_a.id,
                original_filename="duplicate.png",
                media_type="image/png",
                file_size_bytes=1048576,
                checksum_sha256="d" * 64,
            ),
            storage_path="assets/scan_01.png",  # Already registered
        )
    assert "storage_path" in str(exc_info.value)


def test_clinical_service_analysis_run_consistency(service_session: Session) -> None:
    """Verify analysis run creation enforces patient and encounter alignment with assets."""
    service = ClinicalService(service_session)

    pat_a = service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-PAT-000A"))
    pat_b = service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-PAT-000B"))

    enc_a = service.create_encounter(
        EncounterCreate(
            patient_id=pat_a.id,
            start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
        )
    )

    asset_a = service.register_asset_metadata(
        data=AssetMetadataCreate(
            patient_id=pat_a.id,
            encounter_id=enc_a.id,
            original_filename="scan_a.png",
            media_type="image/png",
            file_size_bytes=1048576,
            checksum_sha256="e" * 64,
        ),
        storage_path="assets/scan_a.png",
    )

    asset_b = service.register_asset_metadata(
        data=AssetMetadataCreate(
            patient_id=pat_b.id,
            original_filename="scan_b.png",
            media_type="image/png",
            file_size_bytes=1048576,
            checksum_sha256="f" * 64,
        ),
        storage_path="assets/scan_b.png",
    )

    # 1. Consistent analysis run
    run = service.create_analysis_run(
        data=AnalysisRunCreate(
            patient_id=pat_a.id,
            encounter_id=enc_a.id,
            asset_id=asset_a.id,
            model_name="cxr_classifier",
            model_version="v1.0.0",
        )
    )
    assert run.id is not None
    assert run.patient_id == pat_a.id
    assert run.status == "queued"

    # 2. Inconsistent asset patient (asset_b belongs to Patient B, but analysis claims Patient A)
    with pytest.raises(ConsistencyError) as exc_info:
        service.create_analysis_run(
            data=AnalysisRunCreate(
                patient_id=pat_a.id,
                encounter_id=enc_a.id,
                asset_id=asset_b.id,  # Belongs to Patient B
                model_name="cxr_classifier",
                model_version="v1.0.0",
            )
        )
    assert "does not match analysis patient" in str(exc_info.value)

    # 3. Update status and verify results container
    updated_run = service.update_analysis_status(
        run_id=run.id,
        status="completed",
        results_summary={"probability": 0.08, "disclaimer": "DEMO ONLY"},
    )
    assert updated_run.status == "completed"
    assert updated_run.results_summary["probability"] == 0.08


def test_service_transaction_rollback_boundary(service_session: Session) -> None:
    """Verify that transaction boundaries are caller-owned and rollback cleanly on error."""
    clinical_service = ClinicalService(service_session)
    user_service = UserService(service_session)

    # Execute a multi-operation workflow inside an explicit caller transaction
    try:
        with service_session.begin():
            clinical_service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-TX-0001"))
            user_service.create_user(
                UserCreate(
                    username="tx_user",
                    email="tx@hospital.org",
                    full_name="Transaction User",
                    password="ValidPassword123",
                )
            )
            # Intentionally simulate a failure mid-transaction
            raise RuntimeError("Simulated mid-transaction failure")
    except RuntimeError:
        pass

    # Verify that the entire transaction was discarded: neither patient nor user was persisted
    assert clinical_service.get_patient_by_mrn("SYNTH-TX-0001") is None
    assert user_service.get_user_by_username("tx_user") is None


def test_service_does_not_prematurely_rollback_caller_transaction_on_handled_error(
    service_session: Session,
) -> None:
    """Verify that domain services do NOT issue session.rollback() on domain errors.

    The outer caller retains full ownership of the transaction and can catch domain
    errors (such as duplicate MRN or validation errors) without having their active
    transaction invalidated or aborted by the service layer.
    """
    clinical_service = ClinicalService(service_session)
    user_service = UserService(service_session)

    with service_session.begin():
        # 1. Caller starts transaction and creates patient 1
        p1 = clinical_service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-TX-RETAIN-1"))
        assert p1.id is not None

        # 2. Service raises DuplicateEntityError because MRN already exists
        with pytest.raises(DuplicateEntityError):
            clinical_service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-TX-RETAIN-1"))

        # 3. CRITICAL PROOF: Because clinical_service did NOT call session.rollback(),
        # the caller's transaction is still valid and can continue normally.
        p2 = clinical_service.create_patient(PatientCreate(mrn_pseudonym="SYNTH-TX-RETAIN-2"))
        assert p2.id is not None

        user = user_service.create_user(
            UserCreate(
                username="tx_resilient_user",
                email="resilient@hospital.org",
                full_name="Resilient User",
                password="ValidPassword123",
            )
        )
        assert user.id is not None

    # After the caller's transaction completes and commits, valid entities are persisted
    assert clinical_service.get_patient_by_mrn("SYNTH-TX-RETAIN-1") is not None
    assert clinical_service.get_patient_by_mrn("SYNTH-TX-RETAIN-2") is not None
    assert user_service.get_user_by_username("tx_resilient_user") is not None


def test_audit_service_sensitive_field_sanitization(service_session: Session) -> None:
    """Verify that credentials, passwords, and tokens are scrubbed from audit metadata."""
    audit_service = AuditService(service_session)

    dirty_metadata = {
        "username": "dr_patel",
        "password": "ClearTextPassword!",
        "hashed_password": "argon2id$v=19$m=65536...",
        "secret_key": "supersecretkey",
        "nested": {
            "access_token": "bearer_jwt_token_here",
            "safe_field": 12345,
        },
    }

    sanitized = sanitize_audit_metadata(dirty_metadata)
    assert sanitized is not None
    assert sanitized["username"] == "dr_patel"
    assert sanitized["password"] == "[REDACTED_CREDENTIAL]"
    assert sanitized["hashed_password"] == "[REDACTED_CREDENTIAL]"
    assert sanitized["secret_key"] == "[REDACTED_CREDENTIAL]"
    assert sanitized["nested"]["access_token"] == "[REDACTED_CREDENTIAL]"
    assert sanitized["nested"]["safe_field"] == 12345

    # Record event through service and verify in database
    event = audit_service.record_event(
        event_type="test.sanitization",
        action="execute",
        description="Testing credential redaction",
        event_metadata=dirty_metadata,
    )
    service_session.flush()

    persisted = audit_service.get_event(event.id)
    assert persisted is not None
    assert persisted.event_metadata["password"] == "[REDACTED_CREDENTIAL]"
    assert persisted.event_metadata["nested"]["access_token"] == "[REDACTED_CREDENTIAL]"


def test_synthetic_data_awareness_and_disclaimers(service_session: Session) -> None:
    """Verify that synthetic dataset markers and AI output disclaimers remain intact."""
    service = ClinicalService(service_session)

    patient = service.create_patient(
        PatientCreate(
            mrn_pseudonym="SYNTH-COHORT-X",
            is_synthetic=True,
        )
    )
    assert patient.is_synthetic is True

    # Listing with filter
    synthetic_list = service.list_patients(is_synthetic=True)
    assert len(synthetic_list) == 1
    assert synthetic_list[0].mrn_pseudonym == "SYNTH-COHORT-X"

    non_synthetic_list = service.list_patients(is_synthetic=False)
    assert len(non_synthetic_list) == 0
