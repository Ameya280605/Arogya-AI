"""Arogya AI — Dashboard Service Unit Tests.

Module 5, Phase 5.5: Dashboard API Aggregation & Integration.
Verifies service-layer boundary validation, date range integrity,
orchestration of repository aggregations, and composed responses.
"""

from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.schemas.dashboard import DashboardOverviewResponse
from backend.app.services.dashboard import DashboardService
from backend.app.settings import Settings


@pytest.fixture
def service_session() -> Session:
    """Fixture providing an isolated in-memory SQLite session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def settings() -> Settings:
    """Isolated test settings."""
    return Settings(
        app_name="Arogya AI",
        app_env="testing",
        api_prefix="/api/v1",
    )


@pytest.fixture
def service(service_session: Session, settings: Settings) -> DashboardService:
    """Provide DashboardService instance."""
    return DashboardService(session=service_session, settings=settings)


def test_service_returns_valid_response_structure(service: DashboardService):
    """Verify service returns a fully populated DashboardOverviewResponse."""
    result = service.get_overview()
    assert isinstance(result, DashboardOverviewResponse)
    assert result.environment == "testing"
    assert result.patients.total_patients == 0
    assert result.encounters.total_encounters == 0
    assert result.analysis.total_runs == 0
    assert result.reviews.pending_count == 0
    assert result.recent_activity.total_events == 0
    assert result.generated_at is not None


def test_service_rejects_reversed_date_range(service: DashboardService):
    """Verify service raises ValueError when start_date follows end_date."""
    with pytest.raises(ValueError, match="Invalid date range: start_date .* cannot follow end_date"):
        service.get_overview(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
        )


def test_service_rejects_invalid_status_filter(service: DashboardService):
    """Verify service raises ValueError when an unknown status string is provided."""
    with pytest.raises(ValueError, match="Invalid analysis run status filter"):
        service.get_overview(
            status_filter="unsupported_status_xyz",  # type: ignore[arg-type]
        )


def test_service_accepts_valid_parameters(service: DashboardService):
    """Verify service accepts valid date range and canonical status."""
    result = service.get_overview(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        status_filter="completed",
    )
    assert isinstance(result, DashboardOverviewResponse)
    assert result.environment == "testing"
