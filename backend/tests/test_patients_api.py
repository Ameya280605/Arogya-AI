"""Arogya AI — Patient Intelligence API Integration Tests.

Module 6: Patient Intelligence.
Comprehensive end-to-end tests verifying:
- Patient cohort listing, search, filtering, and pagination
- Patient CRUD, schema validation, and uniqueness conflict (409) handling
- Encounter creation, lifecycle status updates, and temporal bounds validation (422)
- Clinical observation recording and cross-entity relationship verification
- Data quality completeness evaluation and unit/physiological warning triggers
- Unified longitudinal timeline stream aggregation
"""

from collections.abc import Generator
from datetime import date, datetime, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.main import create_app
from backend.app.settings import Settings


@pytest.fixture
def test_engine():
    """Isolated SQLite engine for patient API testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(test_engine) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency overrides for isolated database testing."""
    settings = Settings(
        app_name="Arogya AI",
        app_env="testing",
        api_prefix="/api/v1",
    )
    app = create_app(settings)
    session_factory = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    from backend.app.db.models import Role, User
    from backend.app.security.dependencies import get_current_user

    test_user = User(
        id=uuid.uuid4(),
        username="test_clinician",
        email="clinician@test.local",
        full_name="Test Clinician",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="doctor_reviewer")],
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# -----------------------------------------------------------------------------
# 6.1 & 6.2: Patient List & CRUD Tests
# -----------------------------------------------------------------------------


def test_list_patients_empty(client: TestClient) -> None:
    """Verify empty patient list response envelope and pagination contract."""
    response = client.get("/api/v1/patients")
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert data["page_size"] == 20


def test_patient_crud_lifecycle(client: TestClient) -> None:
    """Verify full CRUD lifecycle: register, retrieve, update, and inspect."""
    # 1. Create Patient
    create_payload = {
        "mrn": "SYNTH-PAT-0042",
        "birth_date": "1990-05-15",
        "biological_sex": "female",
        "is_synthetic": True,
    }
    create_res = client.post("/api/v1/patients", json=create_payload)
    assert create_res.status_code == 201
    created = create_res.json()
    patient_id = created["id"]
    assert created["mrn_pseudonym"] == "SYNTH-PAT-0042"
    assert created["birth_date"] == "1990-05-15"
    assert created["biological_sex"] == "female"
    assert created["is_synthetic"] is True

    # 2. Get Patient by ID
    get_res = client.get(f"/api/v1/patients/{patient_id}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["id"] == patient_id
    assert retrieved["mrn_pseudonym"] == "SYNTH-PAT-0042"

    # 3. Update Patient
    update_payload = {
        "birth_date": "1990-05-20",
        "biological_sex": "other",
    }
    patch_res = client.patch(f"/api/v1/patients/{patient_id}", json=update_payload)
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["birth_date"] == "1990-05-20"
    assert updated["biological_sex"] == "other"


def test_patient_duplicate_mrn_conflict(client: TestClient) -> None:
    """Verify unique constraint on MRN pseudonym produces HTTP 409 Conflict."""
    payload = {
        "mrn_pseudonym": "SYNTH-PAT-UNIQUE-001",
        "birth_date": "1985-01-01",
        "biological_sex": "male",
    }
    res1 = client.post("/api/v1/patients", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/v1/patients", json=payload)
    assert res2.status_code == 409
    error_data = res2.json()
    assert "error" in error_data
    assert "already exists" in error_data["error"]["message"].lower()


def test_patient_search_and_filter(client: TestClient) -> None:
    """Verify search by MRN term and filtering by biological sex."""
    client.post(
        "/api/v1/patients",
        json={"mrn": "SYNTH-SEARCH-A", "biological_sex": "female", "birth_date": "1991-01-01"},
    )
    client.post(
        "/api/v1/patients",
        json={"mrn": "SYNTH-SEARCH-B", "biological_sex": "male", "birth_date": "1982-02-02"},
    )
    client.post(
        "/api/v1/patients",
        json={"mrn": "OTHER-PAT-001", "biological_sex": "female", "birth_date": "1975-03-03"},
    )

    # Search filter
    search_res = client.get("/api/v1/patients?search=SEARCH")
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["total"] == 2
    assert all("SEARCH" in p["mrn_pseudonym"] for p in search_data["items"])

    # Sex filter
    sex_res = client.get("/api/v1/patients?biological_sex=male")
    assert sex_res.status_code == 200
    sex_data = sex_res.json()
    assert sex_data["total"] == 1
    assert sex_data["items"][0]["mrn_pseudonym"] == "SYNTH-SEARCH-B"


def test_get_nonexistent_patient_returns_404(client: TestClient) -> None:
    """Verify 404 response when querying nonexistent patient UUID."""
    random_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/patients/{random_id}")
    assert res.status_code == 404
    assert "was not found" in res.json()["error"]["message"]


# -----------------------------------------------------------------------------
# 6.4: Encounters & Observations Tests
# -----------------------------------------------------------------------------


def test_encounter_lifecycle_and_validation(client: TestClient) -> None:
    """Verify encounter creation, temporal validation, and status updates."""
    # Register patient
    pat_res = client.post(
        "/api/v1/patients",
        json={"mrn": "SYNTH-ENC-TEST-PAT", "birth_date": "1985-05-05"},
    )
    patient_id = pat_res.json()["id"]

    # 1. Invalid temporal order: end_time before start_time
    invalid_enc = {
        "encounter_type": "ambulatory",
        "status": "completed",
        "start_time": "2026-10-25T11:00:00Z",
        "end_time": "2026-10-25T10:00:00Z",
    }
    bad_res = client.post(f"/api/v1/patients/{patient_id}/encounters", json=invalid_enc)
    assert bad_res.status_code == 422

    # 2. Valid encounter creation
    valid_enc = {
        "encounter_type": "ambulatory",
        "status": "in_progress",
        "start_time": "2026-10-25T10:00:00Z",
    }
    enc_res = client.post(f"/api/v1/patients/{patient_id}/encounters", json=valid_enc)
    assert enc_res.status_code == 201
    enc_data = enc_res.json()
    encounter_id = enc_data["id"]
    assert enc_data["status"] == "in_progress"
    assert enc_data["patient_id"] == patient_id

    # 3. Retrieve encounter by ID
    get_enc = client.get(f"/api/v1/encounters/{encounter_id}")
    assert get_enc.status_code == 200
    assert get_enc.json()["id"] == encounter_id

    # 4. Update encounter status to completed
    update_res = client.patch(
        f"/api/v1/encounters/{encounter_id}",
        json={"status": "completed", "end_time": "2026-10-25T10:45:00Z"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "completed"

    # 5. List encounters for patient
    list_res = client.get(f"/api/v1/patients/{patient_id}/encounters")
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 1


def test_observation_recording_and_relationship(client: TestClient) -> None:
    """Verify observation recording linked to encounter and longitudinal retrieval."""
    # Register patient and encounter
    pat_res = client.post("/api/v1/patients", json={"mrn": "SYNTH-OBS-PAT"})
    patient_id = pat_res.json()["id"]

    enc_res = client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"start_time": "2026-10-25T09:00:00Z"},
    )
    encounter_id = enc_res.json()["id"]

    # 1. Record vital signs
    obs_payload = {
        "code": "8867-4",
        "display_name": "Heart Rate",
        "numeric_value": 72.0,
        "unit": "bpm",
        "observed_at": "2026-10-25T09:15:00Z",
    }
    obs_res = client.post(f"/api/v1/encounters/{encounter_id}/observations", json=obs_payload)
    assert obs_res.status_code == 201
    obs_data = obs_res.json()
    assert obs_data["numeric_value"] == 72.0
    assert obs_data["unit"] == "bpm"
    assert obs_data["encounter_id"] == encounter_id
    assert obs_data["patient_id"] == patient_id

    # 2. List encounter observations
    enc_obs_res = client.get(f"/api/v1/encounters/{encounter_id}/observations")
    assert enc_obs_res.status_code == 200
    assert enc_obs_res.json()["total"] == 1

    # 3. List patient longitudinal observations
    pat_obs_res = client.get(f"/api/v1/patients/{patient_id}/observations")
    assert pat_obs_res.status_code == 200
    assert pat_obs_res.json()["total"] == 1


# -----------------------------------------------------------------------------
# 6.5: Data Quality Evaluation Tests
# -----------------------------------------------------------------------------


def test_data_quality_evaluation_and_warnings(client: TestClient) -> None:
    """Verify data completeness score and unit/demographic consistency warnings."""
    # 1. Patient with missing birth date and unknown sex
    pat1 = client.post("/api/v1/patients", json={"mrn": "SYNTH-QUALITY-SPARSE"}).json()
    q1_res = client.get(f"/api/v1/patients/{pat1['id']}/quality")
    assert q1_res.status_code == 200
    q1 = q1_res.json()
    # Completeness score should be lower due to missing birth date and no encounters
    assert q1["completeness_score"] < 60
    assert any("Birth date is missing" in i["message"] for i in q1["issues"])

    # 2. Complete patient with encounter and observations
    pat2 = client.post(
        "/api/v1/patients",
        json={"mrn": "SYNTH-QUALITY-COMPLETE", "birth_date": "1980-01-01", "biological_sex": "male"},
    ).json()
    enc2 = client.post(
        f"/api/v1/patients/{pat2['id']}/encounters",
        json={"start_time": "2026-10-25T10:00:00Z"},
    ).json()

    # Add observation with an unphysiological heart rate and missing unit warning trigger
    client.post(
        f"/api/v1/encounters/{enc2['id']}/observations",
        json={
            "code": "8867-4",
            "display_name": "Heart Rate",
            "numeric_value": 260.0,  # Unphysiological tachycardia outlier
            "unit": "bpm",
            "observed_at": "2026-10-25T10:10:00Z",
        },
    )
    client.post(
        f"/api/v1/encounters/{enc2['id']}/observations",
        json={
            "code": "8310-5",
            "display_name": "Body Temperature",
            "numeric_value": 37.0,
            "unit": None,  # Missing unit trigger
            "observed_at": "2026-10-25T10:12:00Z",
        },
    )

    q2_res = client.get(f"/api/v1/patients/{pat2['id']}/quality")
    assert q2_res.status_code == 200
    q2 = q2_res.json()
    assert q2["has_warnings"] is True
    # Verify unphysiological heart rate warning
    assert any("outside plausible physiological bounds" in i["message"] for i in q2["issues"])
    # Verify missing unit warning
    assert any("lacks a standard measurement unit" in i["message"] for i in q2["issues"])


# -----------------------------------------------------------------------------
# 6.3: Timeline Stream Tests
# -----------------------------------------------------------------------------


def test_patient_timeline_stream(client: TestClient) -> None:
    """Verify unified chronological timeline stream across encounters and vitals."""
    pat = client.post(
        "/api/v1/patients",
        json={"mrn": "SYNTH-TIMELINE-PAT", "birth_date": "1995-12-12"},
    ).json()
    patient_id = pat["id"]

    # Add encounter
    enc = client.post(
        f"/api/v1/patients/{patient_id}/encounters",
        json={"start_time": "2026-10-25T08:00:00Z", "encounter_type": "ambulatory"},
    ).json()

    # Add observation
    client.post(
        f"/api/v1/encounters/{enc['id']}/observations",
        json={
            "code": "8867-4",
            "display_name": "Resting Heart Rate",
            "numeric_value": 68.0,
            "unit": "bpm",
            "observed_at": "2026-10-25T08:15:00Z",
        },
    )

    timeline_res = client.get(f"/api/v1/patients/{patient_id}/timeline")
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert timeline["total"] >= 2
    types = [item["event_type"] for item in timeline["items"]]
    assert "encounter" in types
    assert "observation" in types
