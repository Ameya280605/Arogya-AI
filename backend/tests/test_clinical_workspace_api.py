"""Integration tests for the patient-scoped clinical workspace workflow."""

from collections.abc import Generator
from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.db.models import Role, User, patient_access
from backend.app.main import create_app
from backend.app.security.dependencies import get_current_user
from backend.app.services.clinical import ClinicalService
from backend.app.settings import Settings


def _client(tmp_path) -> tuple[TestClient, sessionmaker[Session], User]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    user = User(
        id=uuid.uuid4(),
        username="workspace_reviewer",
        email="workspace@test.local",
        full_name="Workspace Reviewer",
        is_active=True,
        roles=[Role(id=uuid.uuid4(), name="doctor_reviewer")],
    )
    app = create_app(
        Settings(
            app_name="Arogya AI",
            app_env="testing",
            api_prefix="/api/v1",
            upload_storage_dir=str(tmp_path / "uploads"),
        )
    )

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user
    return TestClient(app), session_factory, user


def _create_patient(client: TestClient, suffix: str) -> str:
    response = client.post(
        "/api/v1/patients",
        json={"mrn_pseudonym": f"SYNTH-WORKSPACE-{suffix}", "is_synthetic": True},
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_case_draft_roundtrip_and_unit_aware_quality(tmp_path) -> None:
    client, _, _ = _client(tmp_path)
    patient_id = _create_patient(client, "CASE")
    response = client.post(
        f"/api/v1/patients/{patient_id}/cases",
        json={
            "status": "draft",
            "symptoms": "Synthetic cough report",
            "symptom_duration": "2 days",
            "medical_history": "Synthetic history",
            "medications": ["Synthetic medication"],
            "allergies": ["Synthetic allergy"],
            "measurements": [
                {
                    "kind": "vital",
                    "code": "temperature",
                    "display_name": "Temperature",
                    "numeric_value": 98.6,
                    "unit": "°F",
                },
            ],
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["status"] == "draft"
    assert created["observations"][0]["numeric_value"] == 98.6
    assert created["observations"][0]["unit"] == "°F"
    assert len(created["observations"]) == 1
    assert created["analysis_runs"] == []
    assert created["quality"]["ready_for_analysis"] is True

    case_id = created["id"]
    listed = client.get(f"/api/v1/patients/{patient_id}/cases")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [case_id]
    updated = client.patch(
        f"/api/v1/cases/{case_id}",
        json={"clinical_notes": "Updated synthetic note", "measurements": []},
    )
    assert updated.status_code == 200
    assert updated.json()["clinical_notes"] == "Updated synthetic note"
    assert updated.json()["observations"] == []
    assert updated.json()["analysis_runs"] == []


def test_data_quality_blocks_invalid_units_but_preserves_original_values(tmp_path) -> None:
    client, _, _ = _client(tmp_path)
    patient_id = _create_patient(client, "QUALITY")
    response = client.post(
        f"/api/v1/patients/{patient_id}/cases",
        json={
            "symptoms": "Synthetic symptom",
            "measurements": [
                {
                    "kind": "vital",
                    "code": "8310-5",
                    "display_name": "Temperature",
                    "numeric_value": 37,
                    "unit": "kelvin",
                }
            ],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["observations"][0]["numeric_value"] == 37
    assert body["observations"][0]["unit"] == "kelvin"
    assert body["quality"]["ready_for_analysis"] is False
    assert "°C or °F" in body["quality"]["blocking_errors"][0]


def test_patient_access_is_required_for_case_retrieval(tmp_path) -> None:
    client, session_factory, _ = _client(tmp_path)
    patient_id = _create_patient(client, "ACCESS")
    session = session_factory()
    session.execute(delete(patient_access).where(patient_access.c.patient_id == uuid.UUID(patient_id)))
    session.commit()
    session.close()
    response = client.get(f"/api/v1/patients/{patient_id}/cases")
    assert response.status_code == 404


def test_case_attachment_upload_and_removal(tmp_path) -> None:
    client, _, _ = _client(tmp_path)
    patient_id = _create_patient(client, "ASSET")
    case_response = client.post(
        f"/api/v1/patients/{patient_id}/cases",
        json={"symptoms": "Synthetic symptoms"},
    )
    case_id = case_response.json()["id"]
    upload = client.post(
        "/api/v1/assets/upload",
        data={"patient_id": patient_id, "encounter_id": case_id},
        files={"file": ("note.pdf", b"%PDF-1.4\nsynthetic test document", "application/pdf")},
    )
    assert upload.status_code == 201
    asset = upload.json()
    case = client.get(f"/api/v1/cases/{case_id}").json()
    assert [item["id"] for item in case["attachments"]] == [asset["id"]]
    stored = tmp_path / "uploads" / asset["storage_path"]
    assert stored.is_file()
    removed = client.delete(f"/api/v1/assets/{asset['id']}")
    assert removed.status_code == 204
    assert not stored.exists()
    assert client.get(f"/api/v1/cases/{case_id}").json()["attachments"] == []

    invalid_upload = client.post(
        "/api/v1/assets/upload",
        data={"patient_id": patient_id, "encounter_id": case_id},
        files={"file": ("bad.png", b"not a PNG", "image/png")},
    )
    assert invalid_upload.status_code == 422


def test_analysis_draft_submission_duplicate_guard_and_retry(tmp_path, monkeypatch) -> None:
    client, session_factory, _ = _client(tmp_path)
    patient_id = _create_patient(client, "RUN")
    case_response = client.post(
        f"/api/v1/patients/{patient_id}/cases",
        json={"symptoms": "Synthetic symptoms", "symptom_duration": "1 day"},
    )
    case_id = case_response.json()["id"]
    draft_response = client.post(
        f"/api/v1/cases/{case_id}/analysis-runs",
        json={
            "analysis_type": "tabular",
            "submit_now": False,
            "tabular_input": {"age": 34, "gender": 0, "smoking": 1},
        },
    )
    assert draft_response.status_code == 201
    draft = draft_response.json()
    assert draft["status"] == "draft"

    class FailedTabularService:
        def __init__(self, session: Session) -> None:
            self.session = session
            self.predictor = SimpleNamespace(
                model_name="tabular_exasens_baseline",
                model_version="test-version",
            )

        def execute_patient_tabular_analysis(
            self,
            *,
            patient_id,
            request_data,
            actor_id,
            run_id,
            before_inference,
        ):
            clinical = ClinicalService(self.session)
            clinical.update_analysis_status(run_id, "running", started_at=datetime.now(timezone.utc), actor_id=actor_id)
            before_inference()
            return clinical.update_analysis_status(
                run_id,
                "failed",
                error_message="Synthetic service unavailable.",
                completed_at=datetime.now(timezone.utc),
                actor_id=actor_id,
            )

    import backend.app.api.clinical_workspace as workspace_api

    monkeypatch.setattr(workspace_api, "TabularMLService", FailedTabularService)
    submitted = client.post(f"/api/v1/analysis-runs/{draft['id']}/submit")
    assert submitted.status_code == 200
    assert submitted.json()["status"] == "failed"
    assert submitted.json()["error_message"] == "Synthetic service unavailable."
    assert client.post(f"/api/v1/analysis-runs/{draft['id']}/submit").status_code == 409

    retry = client.post(f"/api/v1/analysis-runs/{draft['id']}/retry")
    assert retry.status_code == 201
    assert retry.json()["id"] != draft["id"]
    assert retry.json()["status"] == "failed"
    original = client.get(f"/api/v1/analysis-runs/{draft['id']}").json()
    assert original["retry_count"] == 1


@pytest.mark.parametrize(
    ("analysis_payload", "updated_payload", "expected_model", "expected_input"),
    [
        (
            {"analysis_type": "tabular", "tabular_input": {"age": 34}},
            {"analysis_type": "tabular", "tabular_input": {"age": 35, "smoking": 2}},
            "tabular_exasens_baseline",
            {"age": 35, "smoking": 2},
        ),
        (
            {"analysis_type": "imaging"},
            {"analysis_type": "imaging", "generate_heatmap": True},
            "cxr_densenet121_nih",
            {"asset_id": None, "generate_heatmap": True, "heatmap_label": "Pneumonia"},
        ),
    ],
)
def test_partial_analysis_drafts_upsert_and_persist_without_inference(
    tmp_path,
    analysis_payload,
    updated_payload,
    expected_model,
    expected_input,
) -> None:
    client, _, _ = _client(tmp_path)
    patient_id = _create_patient(client, f"PARTIAL-{expected_model}")
    case = client.post(
        f"/api/v1/patients/{patient_id}/cases",
        json={"status": "draft"},
    ).json()

    first = client.post(
        f"/api/v1/cases/{case['id']}/analysis-runs",
        json={"submit_now": False, **analysis_payload},
    )
    assert first.status_code == 201
    first_run = first.json()
    assert first_run["status"] == "draft"
    assert first_run["model_name"] == expected_model
    assert first_run["started_at"] is None
    assert first_run["results_summary"] is None

    second = client.post(
        f"/api/v1/cases/{case['id']}/analysis-runs",
        json={"submit_now": False, **updated_payload},
    )
    assert second.status_code == 201
    saved_run = second.json()
    assert saved_run["id"] == first_run["id"]
    assert saved_run["draft_input"] == expected_input

    refreshed_case = client.get(f"/api/v1/cases/{case['id']}")
    assert refreshed_case.status_code == 200
    case_runs = refreshed_case.json()["analysis_runs"]
    assert len(case_runs) == 1
    assert case_runs[0]["id"] == first_run["id"]
    assert case_runs[0]["patient_id"] == patient_id
    assert case_runs[0]["encounter_id"] == case["id"]
    assert case_runs[0]["status"] == "draft"
    persisted = client.get(f"/api/v1/analysis-runs/{first_run['id']}")
    assert persisted.status_code == 200
    assert persisted.json()["draft_input"] == expected_input


@pytest.mark.parametrize(
    ("analysis_payload", "expected_message"),
    [
        (
            {"analysis_type": "tabular", "tabular_input": {"age": 34}},
            "required tabular inputs",
        ),
        (
            {"analysis_type": "imaging"},
            "PNG or JPEG image",
        ),
    ],
)
def test_partial_analysis_drafts_still_require_valid_inputs_for_submission(
    tmp_path,
    analysis_payload,
    expected_message,
) -> None:
    client, _, _ = _client(tmp_path)
    patient_id = _create_patient(client, f"SUBMIT-PARTIAL-{expected_message}")
    case = client.post(
        f"/api/v1/patients/{patient_id}/cases",
        json={"symptoms": "Synthetic symptoms"},
    ).json()
    saved = client.post(
        f"/api/v1/cases/{case['id']}/analysis-runs",
        json={"submit_now": False, **analysis_payload},
    )
    assert saved.status_code == 201

    submitted = client.post(f"/api/v1/analysis-runs/{saved.json()['id']}/submit")
    assert submitted.status_code == 422
    assert expected_message in str(submitted.json())
    still_draft = client.get(f"/api/v1/analysis-runs/{saved.json()['id']}").json()
    assert still_draft["status"] == "draft"
    assert still_draft["started_at"] is None
    assert still_draft["results_summary"] is None


def test_successful_case_analysis_requires_and_records_human_review(tmp_path, monkeypatch) -> None:
    client, _, _ = _client(tmp_path)
    patient_id = _create_patient(client, "REVIEW")
    case = client.post(
        f"/api/v1/patients/{patient_id}/cases",
        json={"symptoms": "Synthetic symptoms"},
    ).json()

    class CompletedTabularService:
        def __init__(self, session: Session) -> None:
            self.session = session
            self.predictor = SimpleNamespace(
                model_name="tabular_exasens_baseline",
                model_version="test-version",
            )

        def execute_patient_tabular_analysis(
            self,
            *,
            patient_id,
            request_data,
            actor_id,
            run_id,
            before_inference,
        ):
            clinical = ClinicalService(self.session)
            clinical.update_analysis_status(run_id, "running", started_at=datetime.now(timezone.utc), actor_id=actor_id)
            before_inference()
            return clinical.update_analysis_status(
                run_id,
                "completed",
                results_summary=None,
                completed_at=datetime.now(timezone.utc),
                actor_id=actor_id,
            )

    import backend.app.api.clinical_workspace as workspace_api

    monkeypatch.setattr(workspace_api, "TabularMLService", CompletedTabularService)
    submitted = client.post(
        f"/api/v1/cases/{case['id']}/analysis-runs",
        json={
            "analysis_type": "tabular",
            "submit_now": True,
            "tabular_input": {"age": 34, "gender": 0, "smoking": 1},
        },
    )
    assert submitted.status_code == 201
    run = submitted.json()
    assert run["status"] == "needs_review"
    assert run["started_at"] is not None
    assert run["completed_at"] is not None

    reviewed = client.post(f"/api/v1/analysis-runs/{run['id']}/review")
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "completed"
    assert client.post(f"/api/v1/analysis-runs/{run['id']}/review").status_code == 409
