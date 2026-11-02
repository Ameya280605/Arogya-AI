"""API integration tests for research-only chest X-ray analysis."""

from collections.abc import Generator
from pathlib import Path
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.db.models import (
    AnalysisRun,
    Patient,
    Role,
    UploadedAsset,
    User,
    patient_access,
)
from backend.app.main import create_app
from backend.app.security.dependencies import get_current_user
from backend.app.settings import Settings


@pytest.fixture
def imaging_engine():
    """Isolated database for imaging API integration tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def imaging_context(imaging_engine, tmp_path: Path):
    """Create an authenticated client, patients, and image assets."""
    session_factory = sessionmaker(
        bind=imaging_engine,
        autoflush=False,
        autocommit=False,
    )
    session = session_factory()

    patient = Patient(
        id=uuid.uuid4(),
        mrn_pseudonym="SYNTH-IMAGING-001",
        is_synthetic=True,
    )
    other_patient = Patient(
        id=uuid.uuid4(),
        mrn_pseudonym="SYNTH-IMAGING-002",
        is_synthetic=True,
    )
    user_id = uuid.uuid4()
    storage_dir = tmp_path / "uploads"
    storage_dir.mkdir()
    image_path = storage_dir / "chest.png"
    image_path.write_bytes(b"test image")

    image_asset = UploadedAsset(
        id=uuid.uuid4(),
        patient_id=patient.id,
        original_filename="chest.png",
        media_type="image/png",
        file_size_bytes=10,
        storage_path="chest.png",
        checksum_sha256="a" * 64,
    )
    foreign_asset = UploadedAsset(
        id=uuid.uuid4(),
        patient_id=other_patient.id,
        original_filename="other.png",
        media_type="image/png",
        file_size_bytes=10,
        storage_path="other.png",
        checksum_sha256="b" * 64,
    )
    dicom_asset = UploadedAsset(
        id=uuid.uuid4(),
        patient_id=patient.id,
        original_filename="chest.dcm",
        media_type="application/dicom",
        file_size_bytes=10,
        storage_path="chest.dcm",
        checksum_sha256="c" * 64,
    )

    session.add_all(
        [patient, other_patient, image_asset, foreign_asset, dicom_asset]
    )
    session.commit()
    patient_id = patient.id
    other_patient_id = other_patient.id
    image_asset_id = image_asset.id
    foreign_asset_id = foreign_asset.id
    dicom_asset_id = dicom_asset.id
    session.close()

    user = User(
        id=user_id,
        username="imaging_administrator",
        email="imaging-admin@example.test",
        full_name="Imaging Administrator",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="administrator")],
    )
    setup_session = session_factory()
    setup_session.add(user)
    setup_session.flush()
    setup_session.execute(
        patient_access.insert().values(
            patient_id=patient_id,
            user_id=user_id,
            granted_by=user_id,
        )
    )
    setup_session.commit()
    setup_session.close()
    user = User(
        id=user_id,
        username="imaging_administrator",
        email="imaging-admin@example.test",
        full_name="Imaging Administrator",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="administrator")],
    )

    app = create_app(
        Settings(
            app_name="Arogya AI Imaging Tests",
            app_env="testing",
            api_prefix="/api/v1",
            upload_storage_dir=str(storage_dir),
        )
    )

    def override_get_db() -> Generator[Session, None, None]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user

    with TestClient(app) as client:
        yield (
            client,
            session_factory,
            patient_id,
            other_patient_id,
            image_asset_id,
            foreign_asset_id,
            dicom_asset_id,
            storage_dir,
        )
    app.dependency_overrides.clear()


def _request(client: TestClient, patient_id: uuid.UUID, asset_id: uuid.UUID):
    return client.post(
        f"/api/v1/patients/{patient_id}/analysis/imaging",
        json={"asset_id": str(asset_id)},
    )


@pytest.mark.integration
def test_imaging_analysis_requires_authentication(imaging_context):
    client, _, patient_id, _, asset_id, _, _, _ = imaging_context
    client.app.dependency_overrides.pop(get_current_user)

    response = _request(client, patient_id, asset_id)

    assert response.status_code == 401


@pytest.mark.integration
def test_imaging_analysis_forbidden_without_analysis_execute_permission(
    imaging_context,
):
    client, _, patient_id, _, asset_id, _, _, _ = imaging_context
    unprivileged_user = User(
        id=uuid.uuid4(),
        username="imaging_unprivileged",
        email="unprivileged@example.test",
        full_name="Unprivileged User",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="researcher")],
    )
    client.app.dependency_overrides[get_current_user] = lambda: unprivileged_user

    response = _request(client, patient_id, asset_id)

    assert response.status_code == 403
    assert "Insufficient permissions" in str(response.json())


@pytest.mark.integration
def test_imaging_analysis_hides_unassigned_patient(imaging_context):
    client, session_factory, _, other_patient_id, _, foreign_asset_id, _, _ = (
        imaging_context
    )

    response = _request(client, other_patient_id, foreign_asset_id)

    assert response.status_code == 404
    with session_factory() as session:
        assert session.scalar(select(AnalysisRun)) is None


@pytest.mark.integration
def test_imaging_analysis_accepts_valid_request(imaging_context, monkeypatch):
    client, session_factory, patient_id, _, asset_id, _, _, storage_dir = imaging_context
    import backend.app.services.imaging as imaging_service

    monkeypatch.setattr(
        imaging_service,
        "get_settings",
        lambda: Settings(app_env="testing", upload_storage_dir=str(storage_dir)),
    )
    inference_result = {
        "predictions": {"Pneumonia": 0.25},
        "model_name": "cxr_densenet121_nih",
        "model_version": "densenet121-res224-nih",
        "research_only": True,
        "disclaimer": "Research use only.",
    }
    analyze = lambda self, image_path, **kwargs: inference_result
    monkeypatch.setattr(imaging_service.ImagingMLService, "analyze", analyze)

    response = _request(client, patient_id, asset_id)

    assert response.status_code == 201
    data = response.json()
    assert data["patient_id"] == str(patient_id)
    assert data["asset_id"] == str(asset_id)
    assert data["status"] == "completed"
    assert data["results_summary"] == inference_result

    with session_factory() as session:
        stored_run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.id == uuid.UUID(data["id"]))
        )
        assert stored_run is not None
        assert stored_run.status == "completed"


@pytest.mark.integration
def test_imaging_analysis_heatmap_can_be_retrieved(imaging_context, monkeypatch):
    client, session_factory, patient_id, _, asset_id, _, _, storage_dir = (
        imaging_context
    )
    import backend.app.services.imaging as imaging_service

    monkeypatch.setattr(
        imaging_service,
        "get_settings",
        lambda: Settings(app_env="testing", upload_storage_dir=str(storage_dir)),
    )

    def analyze_with_heatmap(self, image_path, **kwargs):
        heatmap_path = kwargs["heatmap_path"]
        heatmap_path.parent.mkdir(parents=True, exist_ok=True)
        heatmap_path.write_bytes(b"test heatmap")
        return {
            "predictions": [{"label": "Pneumonia", "score": 0.25}],
            "gradcam": {
                "label": "Pneumonia",
                "raw_model_score": 0.25,
                "research_only": True,
                "note": "Research only.",
            },
        }

    monkeypatch.setattr(
        imaging_service.ImagingMLService,
        "analyze",
        analyze_with_heatmap,
    )

    response = client.post(
        f"/api/v1/patients/{patient_id}/analysis/imaging",
        json={
            "asset_id": str(asset_id),
            "generate_heatmap": True,
            "heatmap_label": "Pneumonia",
        },
    )

    assert response.status_code == 201
    run_id = response.json()["id"]
    read_only_user = User(
        id=uuid.uuid4(),
        username="heatmap_researcher",
        email="heatmap-researcher@example.test",
        full_name="Heatmap Researcher",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="researcher")],
    )
    with session_factory() as session:
        session.add(read_only_user)
        session.flush()
        read_only_user_id = read_only_user.id
        session.execute(
            patient_access.insert().values(
                patient_id=patient_id,
                user_id=read_only_user_id,
                granted_by=read_only_user_id,
            )
        )
        session.commit()
    read_only_user = User(
        id=read_only_user_id,
        username="heatmap_researcher",
        email="heatmap-researcher@example.test",
        full_name="Heatmap Researcher",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="researcher")],
    )
    client.app.dependency_overrides[get_current_user] = lambda: read_only_user
    heatmap_response = client.get(
        f"/api/v1/analysis-runs/{run_id}/imaging/heatmap"
    )

    assert heatmap_response.status_code == 200
    assert heatmap_response.content == b"test heatmap"
    assert heatmap_response.headers["content-type"] == "image/png"
    assert heatmap_response.headers["cache-control"] == "private, no-store"
    assert str(storage_dir) not in heatmap_response.headers.get(
        "content-disposition", ""
    )


@pytest.mark.integration
def test_heatmap_hides_analysis_run_for_unassigned_patient(imaging_context):
    client, session_factory, _, other_patient_id, _, _, _, storage_dir = (
        imaging_context
    )
    run = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=other_patient_id,
        model_name="cxr_densenet121_nih",
        model_version="test",
        status="completed",
        results_summary={"gradcam": {"label": "Pneumonia"}},
    )
    run_id = run.id
    with session_factory() as session:
        session.add(run)
        session.commit()
    artifact_dir = storage_dir.parent / "imaging_artifacts"
    artifact_dir.mkdir(exist_ok=True)
    (artifact_dir / f"{run_id.hex}.png").write_bytes(b"private heatmap")

    response = client.get(
        f"/api/v1/analysis-runs/{run_id}/imaging/heatmap"
    )

    assert response.status_code == 404
    assert response.content != b"private heatmap"


@pytest.mark.integration
def test_analysis_results_are_hidden_for_unassigned_patient(imaging_context):
    client, session_factory, _, other_patient_id, _, _, _, _ = imaging_context
    run = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=other_patient_id,
        model_name="cxr_densenet121_nih",
        model_version="test",
        status="completed",
        results_summary={"predictions": [{"label": "Pneumonia", "score": 0.9}]},
    )
    with session_factory() as session:
        session.add(run)
        session.commit()

    response = client.get(
        f"/api/v1/patients/{other_patient_id}/analysis-runs"
    )

    assert response.status_code == 404


@pytest.mark.integration
def test_admin_must_grant_patient_access_explicitly(imaging_context):
    client, session_factory, _, other_patient_id, _, _, _, _ = imaging_context
    with session_factory() as session:
        admin_id = session.scalar(
            select(User.id).where(User.username == "imaging_administrator")
        )
    researcher = User(
        id=uuid.uuid4(),
        username="assigned_researcher",
        email="assigned-researcher@example.test",
        full_name="Assigned Researcher",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="researcher")],
    )
    with session_factory() as session:
        session.add(researcher)
        researcher_id = researcher.id
        session.commit()
    researcher = User(
        id=researcher_id,
        username="assigned_researcher",
        email="assigned-researcher@example.test",
        full_name="Assigned Researcher",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="researcher")],
    )

    # Administrator privileges do not bypass patient assignments.
    assert client.get(
        f"/api/v1/patients/{other_patient_id}"
    ).status_code == 404

    grant = client.put(
        f"/api/v1/patients/{other_patient_id}/access/{researcher.id}"
    )
    assert grant.status_code == 204

    client.app.dependency_overrides[get_current_user] = lambda: researcher
    assert client.get(
        f"/api/v1/patients/{other_patient_id}"
    ).status_code == 200
    assert client.get(
        f"/api/v1/patients/{other_patient_id}/assets"
    ).status_code == 200

    client.app.dependency_overrides[get_current_user] = lambda: User(
        id=uuid.uuid4(),
        username="non_admin",
        email="non-admin@example.test",
        full_name="Non Admin",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="researcher")],
    )
    denied_grant = client.put(
        f"/api/v1/patients/{other_patient_id}/access/{researcher.id}"
    )
    assert denied_grant.status_code == 403

    admin_user = User(
        id=admin_id,
        username="imaging_administrator",
        email="imaging-admin@example.test",
        full_name="Imaging Administrator",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="administrator")],
    )
    client.app.dependency_overrides[get_current_user] = lambda: admin_user
    revoke = client.delete(
        f"/api/v1/patients/{other_patient_id}/access/{researcher.id}"
    )
    assert revoke.status_code == 204
    client.app.dependency_overrides[get_current_user] = lambda: researcher
    assert client.get(
        f"/api/v1/patients/{other_patient_id}"
    ).status_code == 404


@pytest.mark.integration
def test_imaging_heatmap_requires_authentication(imaging_context):
    client, _, _, _, _, _, _, _ = imaging_context
    client.app.dependency_overrides.pop(get_current_user)

    response = client.get(
        f"/api/v1/analysis-runs/{uuid.uuid4()}/imaging/heatmap"
    )

    assert response.status_code == 401


@pytest.mark.integration
def test_imaging_heatmap_forbidden_without_analysis_permission(imaging_context):
    client, _, _, _, _, _, _, _ = imaging_context
    unprivileged_user = User(
        id=uuid.uuid4(),
        username="heatmap_unprivileged",
        email="heatmap-unprivileged@example.test",
        full_name="Unprivileged User",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="unprivileged")],
    )
    client.app.dependency_overrides[get_current_user] = lambda: unprivileged_user

    response = client.get(
        f"/api/v1/analysis-runs/{uuid.uuid4()}/imaging/heatmap"
    )

    assert response.status_code == 403


@pytest.mark.integration
@pytest.mark.parametrize(
    ("model_name", "run_status"),
    [
        ("tabular_xgb_risk", "completed"),
        ("cxr_densenet121_nih", "failed"),
    ],
)
def test_imaging_heatmap_rejects_non_completed_imaging_runs(
    imaging_context,
    model_name: str,
    run_status: str,
):
    client, session_factory, patient_id, _, _, _, _, storage_dir = imaging_context
    run = AnalysisRun(
        id=uuid.uuid4(),
        patient_id=patient_id,
        model_name=model_name,
        model_version="test",
        status=run_status,
        results_summary={"gradcam": {"label": "Pneumonia"}},
    )
    with session_factory() as session:
        session.add(run)
        session.commit()
        run_id = run.id

    artifact_dir = storage_dir.parent / "imaging_artifacts"
    artifact_dir.mkdir()
    (artifact_dir / f"{run_id.hex}.png").write_bytes(b"test heatmap")

    response = client.get(
        f"/api/v1/analysis-runs/{run_id}/imaging/heatmap"
    )

    assert response.status_code == 404


@pytest.mark.integration
def test_imaging_analysis_missing_asset_returns_not_found(imaging_context):
    client, _, patient_id, _, _, _, _, _ = imaging_context

    response = _request(client, patient_id, uuid.uuid4())

    assert response.status_code == 404
    assert "asset was not found" in str(response.json()).lower()


@pytest.mark.integration
def test_imaging_analysis_rejects_asset_owned_by_another_patient(imaging_context):
    client, _, patient_id, other_patient_id, _, foreign_asset_id, _, _ = imaging_context
    assert patient_id != other_patient_id

    response = _request(client, patient_id, foreign_asset_id)

    assert response.status_code == 422
    assert "does not belong to this patient" in str(response.json()).lower()


@pytest.mark.integration
@pytest.mark.parametrize(
    ("filename", "media_type"),
    [
        ("chest.dcm", "application/dicom"),
        ("chest.png", "application/pdf"),
    ],
)
def test_imaging_analysis_rejects_unsupported_formats(
    imaging_context,
    filename: str,
    media_type: str,
):
    client, session_factory, patient_id, _, _, _, dicom_asset_id, _ = imaging_context
    # The fixture DICOM asset covers the standard unsupported format. For the
    # unsupported MIME case, update its persisted metadata before the request.
    if media_type == "application/pdf":
        with session_factory() as session:
            asset = session.get(UploadedAsset, dicom_asset_id)
            asset.original_filename = filename
            asset.media_type = media_type
            session.commit()

    response = _request(client, patient_id, dicom_asset_id)

    assert response.status_code == 422
    assert "supports png and jpeg" in str(response.json()).lower()


@pytest.mark.integration
def test_imaging_analysis_records_inference_failure(imaging_context, monkeypatch):
    client, session_factory, patient_id, _, asset_id, _, _, storage_dir = imaging_context
    import backend.app.services.imaging as imaging_service

    monkeypatch.setattr(
        imaging_service,
        "get_settings",
        lambda: Settings(app_env="testing", upload_storage_dir=str(storage_dir)),
    )

    def fail_inference(self, image_path, **kwargs):
        raise RuntimeError("Simulated inference failure")

    monkeypatch.setattr(
        imaging_service.ImagingMLService,
        "analyze",
        fail_inference,
    )

    response = _request(client, patient_id, asset_id)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "failed"
    assert data["error_message"] == "Imaging analysis failed. Check server logs."
    assert data["completed_at"] is not None

    with session_factory() as session:
        stored_run = session.scalar(
            select(AnalysisRun).where(AnalysisRun.id == uuid.UUID(data["id"]))
        )
        assert stored_run is not None
        assert stored_run.status == "failed"
