"""Arogya AI - Pydantic API Data Contract Tests.

Module 3, Phase 3.4: Pydantic Request/Response Schemas & Data Contracts.
Validates request payload validation, rejection of missing/invalid/extra fields,
exclusion of sensitive database fields, and ORM model serialization parity.
"""

from datetime import date, datetime, timezone
import uuid
import pytest
from pydantic import ValidationError

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
from backend.app.schemas import (
    AnalysisRunCreate,
    AnalysisRunResponse,
    AssetMetadataCreate,
    AssetMetadataResponse,
    AuditEventFilter,
    AuditEventResponse,
    EncounterCreate,
    EncounterResponse,
    EncounterUpdate,
    ObservationCreate,
    ObservationResponse,
    PaginatedResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    RoleCreate,
    RoleResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)


# ---------------------------------------------------------------------------
# 1. Valid Request Payloads Accepted
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_valid_request_payloads_accepted():
    """Verify that syntactically valid request payloads across all domains instantiate cleanly."""
    # User & Role
    role_req = RoleCreate(name="clinician", description="Reviewing clinician")
    assert role_req.name == "clinician"

    user_req = UserCreate(
        username="dr_sarah",
        email="sarah.smith@hospital.org",
        full_name="Dr. Sarah Smith",
        password="SecurePassword#2026",
    )
    assert user_req.username == "dr_sarah"

    # Patient
    patient_req = PatientCreate(
        mrn_pseudonym="SYNTH-PAT-0099",
        birth_date=date(1990, 8, 20),
        biological_sex="female",
        is_synthetic=True,
    )
    assert patient_req.mrn_pseudonym == "SYNTH-PAT-0099"

    # Encounter
    patient_uuid = uuid.uuid4()
    encounter_req = EncounterCreate(
        patient_id=patient_uuid,
        encounter_type="ambulatory",
        status="in_progress",
        start_time=datetime(2026, 10, 25, 9, 30, tzinfo=timezone.utc),
    )
    assert encounter_req.patient_id == patient_uuid

    # Observation
    encounter_uuid = uuid.uuid4()
    obs_req = ObservationCreate(
        encounter_id=encounter_uuid,
        patient_id=patient_uuid,
        code="8867-4",
        display_name="Heart Rate",
        numeric_value=74.5,
        unit="bpm",
        observed_at=datetime(2026, 10, 25, 9, 45, tzinfo=timezone.utc),
    )
    assert obs_req.numeric_value == 74.5

    # Asset Metadata
    asset_req = AssetMetadataCreate(
        patient_id=patient_uuid,
        encounter_id=encounter_uuid,
        original_filename="chest_scan.png",
        media_type="image/png",
        file_size_bytes=2097152,
        checksum_sha256="a" * 64,
    )
    assert asset_req.file_size_bytes == 2097152

    # Analysis Run
    run_req = AnalysisRunCreate(
        patient_id=patient_uuid,
        encounter_id=encounter_uuid,
        model_name="cxr_densenet121_baseline",
        model_version="0.1.0-alpha",
        parameters={"confidence_threshold": 0.6},
    )
    assert run_req.model_name == "cxr_densenet121_baseline"

    # Audit Filter
    audit_filter = AuditEventFilter(
        event_type="user.login",
        start_time=datetime(2026, 10, 25, 0, 0, tzinfo=timezone.utc),
    )
    assert audit_filter.event_type == "user.login"


# ---------------------------------------------------------------------------
# 2. Missing Required Fields Rejected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_missing_required_fields_rejected():
    """Verify that payloads missing mandatory fields raise ValidationError."""
    # Missing username
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            email="test@hospital.org",
            full_name="Tester",
            password="Password123",
        )
    assert "username" in str(exc.value)

    # Missing mrn_pseudonym
    with pytest.raises(ValidationError) as exc:
        PatientCreate(
            birth_date=date(1980, 1, 1),
        )
    assert "mrn_pseudonym" in str(exc.value)

    # Missing patient_id on encounter
    with pytest.raises(ValidationError) as exc:
        EncounterCreate(
            start_time=datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc),
        )
    assert "patient_id" in str(exc.value)

    # Missing observed_at on observation
    with pytest.raises(ValidationError) as exc:
        ObservationCreate(
            encounter_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            code="temp",
            display_name="Temperature",
            numeric_value=37.0,
        )
    assert "observed_at" in str(exc.value)


# ---------------------------------------------------------------------------
# 3. Invalid Formats & Range Violations Rejected
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_invalid_email_format_rejected():
    """Verify malformed email formats are rejected."""
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            username="test_user",
            email="not_a_valid_email",
            full_name="Test User",
            password="Password123",
        )
    assert "email" in str(exc.value)


@pytest.mark.unit
def test_invalid_uuid_format_rejected():
    """Verify malformed UUID strings are rejected."""
    with pytest.raises(ValidationError) as exc:
        EncounterCreate(
            patient_id="not-a-valid-uuid",  # type: ignore[arg-type]
            start_time=datetime.now(timezone.utc),
        )
    assert "patient_id" in str(exc.value)


@pytest.mark.unit
def test_username_length_and_pattern_constraints():
    """Verify username bounds (<3 characters or illegal symbols) are rejected."""
    # Too short (< 3)
    with pytest.raises(ValidationError):
        UserCreate(username="ab", email="ab@h.org", full_name="AB", password="pass123456")

    # Invalid characters (spaces, special punctuation)
    with pytest.raises(ValidationError):
        UserCreate(username="user with spaces", email="u@h.org", full_name="U", password="pass123456")


@pytest.mark.unit
def test_naive_timestamp_rejected():
    """Verify that timestamps lacking timezone information are rejected."""
    # Naive start_time on EncounterCreate
    with pytest.raises(ValidationError) as exc:
        EncounterCreate(
            patient_id=uuid.uuid4(),
            start_time=datetime(2026, 10, 25, 10, 0),  # Naive (no tzinfo)
        )
    assert "timezone-aware" in str(exc.value)

    # Naive observed_at on ObservationCreate
    with pytest.raises(ValidationError) as exc:
        ObservationCreate(
            encounter_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            code="hr",
            display_name="Heart Rate",
            numeric_value=70.0,
            observed_at=datetime(2026, 10, 25, 10, 0),  # Naive
        )
    assert "timezone-aware" in str(exc.value)


@pytest.mark.unit
def test_encounter_temporal_order_constraint():
    """Verify encounter end_time cannot be earlier than start_time."""
    start = datetime(2026, 10, 25, 11, 0, tzinfo=timezone.utc)
    earlier_end = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError) as exc:
        EncounterCreate(
            patient_id=uuid.uuid4(),
            start_time=start,
            end_time=earlier_end,
        )
    assert "end_time cannot be earlier than start_time" in str(exc.value)


@pytest.mark.unit
def test_observation_requires_numeric_or_text_value():
    """Verify observation creation fails if neither numeric_value nor text_value is provided."""
    with pytest.raises(ValidationError) as exc:
        ObservationCreate(
            encounter_id=uuid.uuid4(),
            patient_id=uuid.uuid4(),
            code="8867-4",
            display_name="Heart Rate",
            numeric_value=None,
            text_value=None,
            observed_at=datetime.now(timezone.utc),
        )
    assert "either 'numeric_value' or 'text_value'" in str(exc.value)


@pytest.mark.unit
def test_asset_checksum_and_file_size_validation():
    """Verify file_size_bytes must be positive and checksum must be a 64-character hex string."""
    # Non-positive size
    with pytest.raises(ValidationError):
        AssetMetadataCreate(
            patient_id=uuid.uuid4(),
            original_filename="scan.png",
            media_type="image/png",
            file_size_bytes=0,
            checksum_sha256="a" * 64,
        )

    # Malformed SHA-256 (wrong length or characters)
    with pytest.raises(ValidationError):
        AssetMetadataCreate(
            patient_id=uuid.uuid4(),
            original_filename="scan.png",
            media_type="image/png",
            file_size_bytes=100,
            checksum_sha256="not_a_valid_sha256_hash",
        )


# ---------------------------------------------------------------------------
# 4. Unknown Fields Rejected (extra="forbid")
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_unknown_fields_rejected_on_request_schemas():
    """Verify request schemas strictly reject unexpected payload attributes."""
    with pytest.raises(ValidationError) as exc:
        UserCreate(
            username="valid_user",
            email="valid@hospital.org",
            full_name="Valid Name",
            password="valid_password_123",
            is_admin=True,  # Unknown / unauthorized field
        )
    assert "extra_forbidden" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        PatientCreate(
            mrn_pseudonym="SYNTH-001",
            unauthorized_field="malicious_payload",
        )
    assert "extra_forbidden" in str(exc.value)


@pytest.mark.unit
def test_asset_metadata_rejects_client_provided_storage_path():
    """Verify clients cannot set internal server storage paths in AssetMetadataCreate."""
    with pytest.raises(ValidationError) as exc:
        AssetMetadataCreate(
            patient_id=uuid.uuid4(),
            original_filename="scan.png",
            media_type="image/png",
            file_size_bytes=1024,
            checksum_sha256="b" * 64,
            storage_path="/etc/passwd",  # Untrusted client path injection attempt
        )
    assert "extra_forbidden" in str(exc.value)


@pytest.mark.unit
def test_analysis_run_create_rejects_client_injected_results_or_status():
    """Verify clients cannot inject trusted model results or override execution status on create."""
    with pytest.raises(ValidationError) as exc:
        AnalysisRunCreate(
            patient_id=uuid.uuid4(),
            model_name="cxr_model",
            model_version="1.0",
            status="completed",  # Client cannot claim run is completed
            results_summary={"diagnosis": "fabricated"},  # Client cannot inject results
        )
    assert "extra_forbidden" in str(exc.value)


# ---------------------------------------------------------------------------
# 5. Sensitive & Security-Internal Field Exclusion
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_password_and_hashes_never_exposed_in_user_response():
    """Verify hashed_password and password never exist in UserResponse, even from ORM models."""
    now = datetime.now(timezone.utc)
    user_orm = User(
        id=uuid.uuid4(),
        username="dr_secure",
        email="secure@hospital.org",
        full_name="Dr. Secure",
        hashed_password="$argon2id$v=19$m=65536,t=3,p=4$SuperSecretHashString",
        is_active=True,
        created_at=now,
        updated_at=now,
        roles=[Role(id=uuid.uuid4(), name="clinician", created_at=now)],
    )

    response = UserResponse.model_validate(user_orm)
    dumped = response.model_dump()

    assert "password" not in dumped
    assert "hashed_password" not in dumped
    assert "SuperSecretHashString" not in str(dumped)
    assert response.username == "dr_secure"
    assert len(response.roles) == 1
    assert response.roles[0].name == "clinician"


# ---------------------------------------------------------------------------
# 6. ORM Model Serialization Parity
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_orm_model_serialization_parity():
    """Verify all domain response schemas serialize representative SQLAlchemy model instances."""
    now = datetime.now(timezone.utc)
    patient_id = uuid.uuid4()
    encounter_id = uuid.uuid4()
    asset_id = uuid.uuid4()

    # Patient
    p_orm = Patient(
        id=patient_id,
        mrn_pseudonym="SYNTH-ORM-01",
        birth_date=date(1975, 3, 10),
        biological_sex="male",
        is_synthetic=True,
        created_at=now,
        updated_at=now,
    )
    p_resp = PatientResponse.model_validate(p_orm)
    assert p_resp.id == patient_id
    assert p_resp.mrn_pseudonym == "SYNTH-ORM-01"

    # Encounter
    e_orm = Encounter(
        id=encounter_id,
        patient_id=patient_id,
        encounter_type="ambulatory",
        status="completed",
        start_time=now,
        end_time=now,
        created_at=now,
        updated_at=now,
    )
    e_resp = EncounterResponse.model_validate(e_orm)
    assert e_resp.id == encounter_id
    assert e_resp.status == "completed"

    # Observation
    obs_orm = Observation(
        id=uuid.uuid4(),
        encounter_id=encounter_id,
        patient_id=patient_id,
        code="9279-1",
        display_name="Respiratory Rate",
        numeric_value=16.0,
        text_value=None,
        unit="breaths/min",
        observed_at=now,
        source_metadata={"sensor_id": "oximeter_01"},
        created_at=now,
    )
    obs_resp = ObservationResponse.model_validate(obs_orm)
    assert obs_resp.numeric_value == 16.0
    assert obs_resp.source_metadata == {"sensor_id": "oximeter_01"}

    # UploadedAsset
    asset_orm = UploadedAsset(
        id=asset_id,
        patient_id=patient_id,
        encounter_id=encounter_id,
        original_filename="lung_xray.png",
        media_type="image/png",
        file_size_bytes=1048576,
        storage_path="assets/2026/10/lung_xray.png",
        checksum_sha256="c" * 64,
        created_at=now,
    )
    asset_resp = AssetMetadataResponse.model_validate(asset_orm)
    assert asset_resp.storage_path == "assets/2026/10/lung_xray.png"

    # AnalysisRun
    run_orm = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=patient_id,
        encounter_id=encounter_id,
        asset_id=asset_id,
        model_name="cxr_densenet121",
        model_version="0.1.0",
        status="completed",
        parameters={"device": "cpu"},
        results_summary={"prob": 0.85},
        error_message=None,
        started_at=now,
        completed_at=now,
        created_at=now,
    )
    run_resp = AnalysisRunResponse.model_validate(run_orm)
    assert run_resp.results_summary == {"prob": 0.85}

    # AuditEvent
    audit_orm = AuditEvent(
        id=uuid.uuid4(),
        event_type="patient.record_created",
        actor_id=uuid.uuid4(),
        action="create",
        resource_type="patient",
        resource_id=str(patient_id),
        description="Created synthetic patient record",
        ip_address="192.168.1.50",
        event_metadata={"request_id": "req-1234"},
        created_at=now,
    )
    audit_resp = AuditEventResponse.model_validate(audit_orm)
    assert audit_resp.event_type == "patient.record_created"
    assert audit_resp.event_metadata == {"request_id": "req-1234"}


# ---------------------------------------------------------------------------
# 7. Generic Pagination Envelope
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generic_paginated_response():
    """Verify PaginatedResponse properly encapsulates collection items and metadata."""
    now = datetime.now(timezone.utc)
    items = [
        RoleResponse(id=uuid.uuid4(), name=f"role_{i}", created_at=now)
        for i in range(3)
    ]
    page = PaginatedResponse[RoleResponse](
        items=items,
        total=15,
        page=1,
        page_size=3,
    )
    assert len(page.items) == 3
    assert page.total == 15
    assert page.page == 1
    assert page.page_size == 3
    dumped = page.model_dump()
    assert dumped["total"] == 15
    assert len(dumped["items"]) == 3
