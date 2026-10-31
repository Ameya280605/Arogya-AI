"""Arogya AI — Dashboard API Integration Tests.

Module 5, Phase 5.5: Dashboard API Aggregation & Integration.
Tests the FastAPI endpoint GET /api/v1/dashboard/overview for:
- Successful database-backed aggregation responses
- Query parameter filtering (start_date, end_date, status)
- Validation error handling on reversed dates and invalid statuses (HTTP 422)
- Database unconfigured/unavailable error envelopes (HTTP 503)
- OpenAPI schema documentation and tag registration
"""

from collections.abc import Generator
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import (
    Base,
    DatabaseConfigurationError,
    DatabaseConnectionError,
    get_db,
)
from backend.app.main import create_app
from backend.app.schemas.dashboard import DashboardOverviewResponse
from backend.app.settings import Settings


@pytest.fixture
def api_engine():
    """Isolated SQLite engine for API tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def api_client(api_engine) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency overrides for isolated SQLite testing."""
    test_settings = Settings(
        app_name="Arogya AI",
        app_env="testing",
        api_prefix="/api/v1",
    )
    app = create_app(test_settings)

    session_factory = sessionmaker(bind=api_engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    from uuid import uuid4
    from backend.app.db.models import Role, User
    from backend.app.security.dependencies import get_current_user

    test_user = User(
        id=uuid4(),
        username="test_clinician",
        email="clinician@test.local",
        full_name="Test Clinician",
        is_active=True,
        roles=[Role(id=uuid4(), name="doctor_reviewer")],
    )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: test_user
    client = TestClient(app)
    try:
        yield client
    finally:
        app.dependency_overrides.clear()


def test_get_dashboard_overview_success(api_client: TestClient):
    """Verify GET /api/v1/dashboard/overview returns 200 and schema-valid payload."""
    response = api_client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200

    data = response.json()
    validated = DashboardOverviewResponse.model_validate(data)
    assert validated.environment == "testing"
    assert validated.patients.total_patients == 0
    assert validated.encounters.total_encounters == 0
    assert validated.analysis.total_runs == 0
    assert validated.reviews.pending_count == 0
    assert validated.recent_activity.total_events == 0


def test_get_dashboard_overview_filters(api_client: TestClient):
    """Verify endpoint accepts date range and canonical status filter parameters."""
    response = api_client.get(
        "/api/v1/dashboard/overview",
        params={
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
            "status": "completed",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["environment"] == "testing"


def test_get_dashboard_overview_reversed_date_range(api_client: TestClient):
    """Verify endpoint returns HTTP 422 when start_date follows end_date."""
    response = api_client.get(
        "/api/v1/dashboard/overview",
        params={
            "start_date": "2026-02-15",
            "end_date": "2026-01-15",
        },
    )
    assert response.status_code == 422
    data = response.json()
    assert "start_date" in str(data) and "cannot follow end_date" in str(data)


def test_get_dashboard_overview_invalid_status(api_client: TestClient):
    """Verify endpoint returns HTTP 422 when an invalid status enum is passed."""
    response = api_client.get(
        "/api/v1/dashboard/overview",
        params={"status": "invalid_lifecycle_state"},
    )
    assert response.status_code == 422


def test_get_dashboard_overview_db_unconfigured(api_client: TestClient):
    """Verify endpoint returns HTTP 503 SERVICE_UNAVAILABLE when database is unconfigured."""
    def override_db_unconfigured():
        raise DatabaseConfigurationError(
            "Database URL is not configured. Set DATABASE_URL in environment."
        )

    api_client.app.dependency_overrides[get_db] = override_db_unconfigured

    response = api_client.get("/api/v1/dashboard/overview")
    assert response.status_code == 503

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert "Database persistence is unconfigured" in data["error"]["message"]


def test_get_dashboard_overview_db_connection_error(api_client: TestClient):
    """Verify endpoint returns HTTP 503 when database connectivity fails."""
    def override_db_conn_error():
        raise DatabaseConnectionError(
            "Connection to PostgreSQL host 'localhost:5432' timed out."
        )

    api_client.app.dependency_overrides[get_db] = override_db_conn_error

    response = api_client.get("/api/v1/dashboard/overview")
    assert response.status_code == 503

    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"


def test_dashboard_route_in_openapi_spec(api_client: TestClient):
    """Verify /api/v1/dashboard/overview is documented in the OpenAPI schema under Dashboard."""
    response = api_client.get("/openapi.json")
    assert response.status_code == 200

    spec = response.json()
    assert "/api/v1/dashboard/overview" in spec["paths"]
    endpoint_spec = spec["paths"]["/api/v1/dashboard/overview"]["get"]
    assert "Dashboard" in endpoint_spec["tags"]
    assert "503" in endpoint_spec["responses"]
    assert "422" in endpoint_spec["responses"]
