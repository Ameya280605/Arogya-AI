from fastapi import HTTPException
"""Arogya AI — Tabular ML API Integration & Regression Tests.

Module 9: Tabular ML Baseline Classification & Biosensor Risk Modeling.
Verifies:
- Authenticated submission of tabular ML inference runs via /api/v1/patients/{id}/analysis/tabular
- Full AnalysisRun persistence and lifecycle transition (queued -> running -> completed/failed)
- Referential integrity with encounters (and 422 on cross-patient mismatch)
- Demographic-only fallback imputation for missing biosensor signals
- Input boundary validation (422) and non-existent patient handling (404)
- RBAC authorization enforcement (401 unauthenticated, 403 forbidden)
- Non-diagnostic research disclosures in API response envelopes
"""

from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import MagicMock
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.db.models import Encounter, Patient, Role, User
from backend.app.main import create_app
from backend.app.schemas.analysis import AnalysisRunResponse
from backend.app.security.dependencies import get_current_user
from backend.app.services.tabular_ml import TabularMLService
from backend.app.settings import Settings


@pytest.fixture
def test_engine():
    """Isolated SQLite engine for tabular analysis API integration testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def session_factory(test_engine):
    """Sessionmaker bound to isolated SQLite engine."""
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def test_user() -> User:
    """Authenticated clinician user holding ANALYSIS_READ and PATIENT permissions."""
    return User(
        id=uuid.uuid4(),
        username="dr_tabular_researcher",
        email="researcher@arogya.local",
        full_name="Dr. Tabular Researcher",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="clinician")],
    )


@pytest.fixture
def client(test_engine, session_factory, test_user) -> Generator[TestClient, None, None]:
    """TestClient bound to test application with isolated SQLite database and user auth."""
    settings = Settings(
        app_name="Arogya AI",
        app_env="testing",
        api_prefix="/api/v1",
    )
    app = create_app(settings)

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_patient(session_factory) -> Patient:
    """Persist and return a synthetic patient for analysis runs."""
    session = session_factory()
    patient = Patient(
        id=uuid.uuid4(),
        mrn_pseudonym=f"SYNTH-TAB-{uuid.uuid4().hex[:6].upper()}",
        birth_date=datetime(1960, 5, 12, tzinfo=timezone.utc).date(),
        biological_sex="male",
        is_synthetic=True,
    )
    session.add(patient)
    session.commit()
    session.refresh(patient)
    session.close()
    return patient


@pytest.fixture
def sample_encounter(session_factory, sample_patient) -> Encounter:
    """Persist and return an encounter belonging to sample_patient."""
    session = session_factory()
    encounter = Encounter(
        id=uuid.uuid4(),
        patient_id=sample_patient.id,
        encounter_type="ambulatory",
        status="in_progress",
        start_time=datetime.now(timezone.utc),
    )
    session.add(encounter)
    session.commit()
    session.refresh(encounter)
    session.close()
    return encounter


@pytest.mark.unit
def test_tabular_analysis_success_complete_biosensors(client: TestClient, sample_patient: Patient):
    """Verify successful tabular inference execution with complete biosensor readings."""
    payload = {
        "age": 65,
        "gender": 1,
        "smoking": 2,
        "imaginary_min": -320.61,
        "imaginary_avg": -300.56,
        "real_min": -495.26,
        "real_avg": -464.17,
        "parameters": {"test_mode": True},
    }

    response = client.post(f"/api/v1/patients/{sample_patient.id}/analysis/tabular", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["patient_id"] == str(sample_patient.id)
    assert data["status"] == "completed"
    assert data["model_name"] == "tabular_exasens_baseline"
    assert data["model_version"] == "0.1.0-alpha"

    # Verify results summary segregation
    res = data["results_summary"]
    assert res is not None
    assert res["predicted_class"] in ("HC", "Asthma", "Infected", "COPD")
    assert "class_probabilities" in res
    assert pytest.approx(sum(res["class_probabilities"].values()), abs=1e-3) == 1.0
    assert res["imputed_features"] == []
    assert res["is_research_prototype"] is True
    assert "RESEARCH PROTOTYPE ONLY" in res["disclaimer"]

    # Verify database persistence via patient analysis runs endpoint
    runs_res = client.get(f"/api/v1/patients/{sample_patient.id}/analysis-runs")
    assert runs_res.status_code == 200
    runs_data = runs_res.json()
    assert runs_data["total"] >= 1
    assert any(r["id"] == data["id"] for r in runs_data["items"])


@pytest.mark.unit
def test_tabular_analysis_success_demographic_only_fallback(client: TestClient, sample_patient: Patient):
    """Verify inference when saliva dielectric readings are omitted (fallback imputation)."""
    payload = {
        "age": 48,
        "gender": 0,
        "smoking": 1,
    }

    response = client.post(f"/api/v1/patients/{sample_patient.id}/analysis/tabular", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["status"] == "completed"
    res = data["results_summary"]
    assert len(res["imputed_features"]) == 4
    assert "Imaginary_Min" in res["imputed_features"]
    assert res["predicted_class"] in ("HC", "Asthma", "Infected", "COPD")


@pytest.mark.unit
def test_tabular_analysis_with_valid_encounter(
    client: TestClient, sample_patient: Patient, sample_encounter: Encounter
):
    """Verify that specifying an encounter records encounter_id in AnalysisRun."""
    payload = {
        "age": 72,
        "gender": 1,
        "smoking": 2,
        "encounter_id": str(sample_encounter.id),
    }

    response = client.post(f"/api/v1/patients/{sample_patient.id}/analysis/tabular", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["encounter_id"] == str(sample_encounter.id)


@pytest.mark.unit
def test_tabular_analysis_consistency_error_mismatched_encounter(
    client: TestClient, sample_patient: Patient, session_factory
):
    """Verify 422 ConsistencyError when encounter belongs to a different patient."""
    session = session_factory()
    other_patient = Patient(
        id=uuid.uuid4(),
        mrn_pseudonym="SYNTH-OTHER-001",
        birth_date=datetime(1980, 1, 1, tzinfo=timezone.utc).date(),
        biological_sex="female",
    )
    other_encounter = Encounter(
        id=uuid.uuid4(),
        patient_id=other_patient.id,
        encounter_type="inpatient",
        status="in_progress",
        start_time=datetime.now(timezone.utc),
    )
    session.add(other_patient)
    session.add(other_encounter)
    session.commit()
    other_encounter_id = other_encounter.id
    session.close()

    payload = {
        "age": 60,
        "gender": 1,
        "smoking": 2,
        "encounter_id": str(other_encounter_id),
    }

    response = client.post(f"/api/v1/patients/{sample_patient.id}/analysis/tabular", json=payload)
    assert response.status_code == 422
    assert "belongs to patient" in response.json()["error"]["message"]


@pytest.mark.unit
def test_tabular_analysis_patient_not_found(client: TestClient):
    """Verify 404 when target patient UUID does not exist."""
    non_existent_id = uuid.uuid4()
    payload = {"age": 50, "gender": 1, "smoking": 1}

    response = client.post(f"/api/v1/patients/{non_existent_id}/analysis/tabular", json=payload)
    assert response.status_code == 404
    assert f"Patient with identifier '{non_existent_id}'" in response.json()["error"]["message"]


@pytest.mark.unit
@pytest.mark.parametrize(
    "bad_payload",
    [
        {"age": 150, "gender": 1, "smoking": 1},  # Age > 120
        {"age": 0, "gender": 1, "smoking": 1},    # Age < 1
        {"age": 50, "gender": 2, "smoking": 1},   # Gender not in {0, 1}
        {"age": 50, "gender": 1, "smoking": 4},   # Smoking not in {1, 2, 3}
        {"gender": 1, "smoking": 1},               # Missing age
    ],
)
def test_tabular_analysis_schema_validation(client: TestClient, sample_patient: Patient, bad_payload: dict):
    """Verify 422 validation error for unphysiological or malformed inputs."""
    response = client.post(f"/api/v1/patients/{sample_patient.id}/analysis/tabular", json=bad_payload)
    assert response.status_code == 422


@pytest.mark.unit
def test_tabular_analysis_unauthenticated(test_engine, session_factory, sample_patient: Patient):
    """Verify 401 Unauthorized when credentials are not supplied."""
    settings = Settings(app_name="Arogya AI", app_env="testing", api_prefix="/api/v1")
    app = create_app(settings)

    def override_get_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as unauthed_client:
        response = unauthed_client.post(
            f"/api/v1/patients/{sample_patient.id}/analysis/tabular",
            json={"age": 50, "gender": 1, "smoking": 1},
        )
        assert response.status_code == 401


@pytest.mark.unit
def test_tabular_analysis_model_failure_handling(
    client: TestClient, sample_patient: Patient, session_factory, monkeypatch
):
    """Verify that internal inference failure updates AnalysisRun status to 'failed'."""
    session = session_factory()
    failing_predictor = MagicMock()
    failing_predictor.model_name = "tabular_exasens_baseline"
    failing_predictor.model_version = "0.1.0-alpha"
    failing_predictor.predict_single.side_effect = RuntimeError("Simulated matrix singularity")

    # Patch get_tabular_predictor to return failing mock
    import backend.app.services.tabular_ml as tab_module
    monkeypatch.setattr(tab_module, "get_tabular_predictor", lambda: failing_predictor)

    payload = {"age": 60, "gender": 1, "smoking": 1}
    response = client.post(f"/api/v1/patients/{sample_patient.id}/analysis/tabular", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "failed"
    assert "Simulated matrix singularity" in data["error_message"]
    assert data["completed_at"] is not None


@pytest.mark.unit
def test_get_tabular_model_info_endpoint(client: TestClient):
    """Verify GET /api/v1/analysis/models/tabular metadata reflection."""
    response = client.get("/api/v1/analysis/models/tabular")
    assert response.status_code == 200
    meta = response.json()

    assert meta["model_name"] == "tabular_exasens_baseline"
    assert meta["model_version"] == "0.1.0-alpha"
    assert "sha256_checksum" in meta
    assert len(meta["sha256_checksum"]) == 64
    assert "RESEARCH PROTOTYPE ONLY" in meta["disclaimer"]


@pytest.mark.unit
def test_tabular_analysis_forbidden_without_analysis_permission(
    client: TestClient,
    sample_patient: Patient,
):
    """Verify actual RBAC denies analysis to a user without permissions."""

    unprivileged_user = User(
        id=uuid.uuid4(),
        username="unprivileged_tabular",
        email="unprivileged_tabular@example.com",
        full_name="Unprivileged User",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="unprivileged")],
    )

    client.app.dependency_overrides[get_current_user] = (
        lambda: unprivileged_user
    )

    response = client.post(
        f"/api/v1/patients/{sample_patient.id}/analysis/tabular",
        json={"age": 50, "gender": 1, "smoking": 1},
    )

    assert response.status_code == 403
    assert "Insufficient permissions" in str(response.json())


@pytest.mark.unit
def test_tabular_model_metadata_forbidden_without_analysis_permission(
    client: TestClient,
):
    """Verify actual RBAC denies model metadata to a user without permissions."""

    unprivileged_user = User(
        id=uuid.uuid4(),
        username="unprivileged_metadata",
        email="unprivileged_metadata@example.com",
        full_name="Unprivileged User",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="unprivileged")],
    )

    client.app.dependency_overrides[get_current_user] = (
        lambda: unprivileged_user
    )

    response = client.get("/api/v1/analysis/models/tabular")

    assert response.status_code == 403
    assert "Insufficient permissions" in str(response.json())
