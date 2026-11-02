"""Arogya AI - Health and Readiness Endpoint Tests.

Validates process liveness (/health), application readiness (/ready),
versioned API prefix mounting, and 404 handling.
"""

import pytest
from fastapi.testclient import TestClient
import backend.app.api.health as health_api
from backend.app.main import create_app
from backend.app.settings import Settings


@pytest.mark.unit
def test_health_endpoint_default_prefix(client: TestClient):
    """Verify GET /api/v1/health returns HTTP 200 and expected liveness fields."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "Arogya AI"


@pytest.mark.unit
def test_readiness_reports_unconfigured_database(monkeypatch, tmp_path):
    """Unconfigured database keeps the service out of readiness."""
    checkpoint = tmp_path / "weights.pt"
    checkpoint.write_bytes(b"checkpoint")
    app = create_app(
        Settings(app_env="testing", database_url=None)
    )
    client = TestClient(app)
    monkeypatch.setattr(
        health_api.ChestXrayInference,
        "checkpoint_path",
        classmethod(lambda cls: checkpoint),
    )
    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        lambda **kwargs: pytest.fail("unconfigured database must not be probed"),
    )

    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["service"] == "Arogya AI"
    assert data["environment"] == client.app.state.settings.app_env
    assert "checks" in data
    assert data["checks"]["core_api"]["status"] == "ready"
    assert data["checks"]["database"]["status"] == "unconfigured"
    assert data["checks"]["ml_inference"]["status"] == "ready"


@pytest.mark.unit
def test_readiness_probes_database_and_checkpoint_without_loading_model(
    monkeypatch, tmp_path
):
    checkpoint = tmp_path / "weights.pt"
    checkpoint.write_bytes(b"checkpoint")
    settings = Settings(
        app_env="testing",
        database_url="postgresql://user:pass@localhost:5432/arogya",
    )
    app = create_app(settings)
    client = TestClient(app)
    database_probe = lambda **kwargs: True

    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        database_probe,
    )
    monkeypatch.setattr(
        health_api,
        "check_database_schema",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        health_api.ChestXrayInference,
        "checkpoint_path",
        classmethod(lambda cls: checkpoint),
    )
    monkeypatch.setattr(
        health_api.ChestXrayInference,
        "__init__",
        lambda self: pytest.fail("readiness must not initialize the model"),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["checks"]["database"]["status"] == "ready"
    assert response.json()["checks"]["ml_inference"]["status"] == "ready"


@pytest.mark.unit
def test_readiness_reports_database_failure_and_missing_checkpoint(
    monkeypatch, tmp_path
):
    from backend.app.db.session import DatabaseConnectionError

    app = create_app(
        Settings(
            app_env="testing",
            database_url="postgresql://user:pass@localhost:5432/arogya",
        )
    )
    client = TestClient(app)
    missing_checkpoint = tmp_path / "missing.pt"

    def failed_database_probe(**kwargs):
        raise DatabaseConnectionError("connection failed")

    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        failed_database_probe,
    )
    monkeypatch.setattr(
        health_api.ChestXrayInference,
        "checkpoint_path",
        classmethod(lambda cls: missing_checkpoint),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    checks = response.json()["checks"]
    assert response.json()["status"] == "not_ready"
    assert checks["database"]["status"] == "not_ready"
    assert checks["ml_inference"]["status"] == "not_ready"


@pytest.mark.unit
def test_readiness_reports_database_migration_mismatch(monkeypatch, tmp_path):
    checkpoint = tmp_path / "weights.pt"
    checkpoint.write_bytes(b"checkpoint")
    app = create_app(
        Settings(
            app_env="testing",
            database_url="postgresql://localhost:5432/arogya",
        )
    )
    client = TestClient(app)
    monkeypatch.setattr(
        health_api,
        "check_database_connection",
        lambda **kwargs: True,
    )
    monkeypatch.setattr(
        health_api,
        "check_database_schema",
        lambda **kwargs: False,
    )
    monkeypatch.setattr(
        health_api.ChestXrayInference,
        "checkpoint_path",
        classmethod(lambda cls: checkpoint),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["database"]["status"] == "not_ready"


@pytest.mark.unit
def test_readiness_reports_empty_model_checkpoint_as_not_ready(
    monkeypatch, tmp_path
):
    empty_checkpoint = tmp_path / "empty-weights.pt"
    empty_checkpoint.touch()
    app = create_app(Settings(app_env="testing", database_url=None))
    client = TestClient(app)
    monkeypatch.setattr(
        health_api.ChestXrayInference,
        "checkpoint_path",
        classmethod(lambda cls: empty_checkpoint),
    )

    response = client.get("/api/v1/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["ml_inference"]["status"] == "not_ready"


@pytest.mark.unit
def test_custom_api_prefix():
    """Verify routes adapt dynamically when api_prefix is changed in settings."""
    custom_settings = Settings(api_prefix="/api/v2", database_url=None)
    custom_app = create_app(custom_settings)
    client = TestClient(custom_app)

    # Verify custom prefix works
    health_resp = client.get("/api/v2/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    ready_resp = client.get("/api/v2/ready")
    assert ready_resp.status_code == 503
    assert ready_resp.json()["status"] == "not_ready"

    # Confirm old prefix returns 404
    old_resp = client.get("/api/v1/health")
    assert old_resp.status_code == 404


@pytest.mark.unit
def test_nonexistent_route_returns_404(client: TestClient):
    """Verify nonexistent routes return HTTP 404."""
    response = client.get("/api/v1/unknown")
    assert response.status_code == 404

    root_response = client.get("/unknown_root")
    assert root_response.status_code == 404
