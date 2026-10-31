"""Arogya AI - Health and Readiness Endpoint Tests.

Validates process liveness (/health), application readiness (/ready),
versioned API prefix mounting, and 404 handling.
"""

import pytest
from fastapi.testclient import TestClient
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
def test_readiness_endpoint_default_prefix(client: TestClient):
    """Verify GET /api/v1/ready returns HTTP 200 and documented readiness status."""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["service"] == "Arogya AI"
    assert data["environment"] == client.app.state.settings.app_env
    assert "checks" in data
    assert data["checks"]["core_api"]["status"] == "ready"
    assert data["checks"]["database"]["status"] == "unconfigured"
    assert data["checks"]["ml_inference"]["status"] == "unconfigured"


@pytest.mark.unit
def test_custom_api_prefix():
    """Verify routes adapt dynamically when api_prefix is changed in settings."""
    custom_settings = Settings(api_prefix="/api/v2")
    custom_app = create_app(custom_settings)
    client = TestClient(custom_app)

    # Verify custom prefix works
    health_resp = client.get("/api/v2/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    ready_resp = client.get("/api/v2/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"

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
