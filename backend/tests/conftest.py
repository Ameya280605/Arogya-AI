"""Arogya AI - Shared Test Fixtures.

Provides isolated application and TestClient fixtures configured for testing.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.settings import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Provide isolated test settings."""
    return Settings(
        app_name="Arogya AI",
        app_env="testing",
        debug=False,
        api_host="127.0.0.1",
        api_port=8000,
        api_prefix="/api/v1",
        log_level="INFO",
    )


@pytest.fixture
def app(test_settings: Settings) -> FastAPI:
    """Provide a fresh FastAPI instance configured with test settings."""
    return create_app(test_settings)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Provide a TestClient bound to the isolated test application."""
    return TestClient(app)
