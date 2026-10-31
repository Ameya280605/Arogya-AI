"""Arogya AI - Settings & Runtime Configuration Hardening Tests.

Verifies type safety, default configurations, environment variable parsing,
normalization, validation failures, production debug restrictions,
documentation disabling mechanisms, and isolated application instances.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic_core import ValidationError
from backend.app.main import create_app
from backend.app.settings import Settings


def test_default_settings() -> None:
    """Verify default settings provide safe local development values."""
    settings = Settings(_env_file=None)
    assert settings.app_name == "Arogya AI"
    assert settings.app_env == "development"
    assert settings.debug is False
    assert settings.api_host == "127.0.0.1"
    assert settings.api_port == 8000
    assert settings.api_prefix == "/api/v1"
    assert settings.log_level == "INFO"
    assert settings.openapi_url == "/openapi.json"
    assert settings.docs_url == "/docs"
    assert settings.redoc_url == "/redoc"
    assert settings.database_url is None
    assert settings.secret_key is None


def test_env_variable_parsing_and_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables are correctly parsed with case normalization."""
    monkeypatch.setenv("APP_NAME", "Arogya Cluster Node")
    monkeypatch.setenv("APP_ENV", "STAGING")
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("API_PORT", "9000")
    monkeypatch.setenv("API_PREFIX", "/api/v2/")

    settings = Settings()
    assert settings.app_name == "Arogya Cluster Node"
    assert settings.app_env == "staging"  # Normalized to lowercase
    assert settings.log_level == "DEBUG"  # Normalized to uppercase
    assert settings.api_port == 9000
    assert settings.api_prefix == "/api/v2"  # Trailing slash stripped


def test_disabling_documentation_via_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Documentation paths set to 'none', 'disabled', or empty parse to None."""
    monkeypatch.setenv("DOCS_URL", "None")
    monkeypatch.setenv("REDOC_URL", "disabled")
    monkeypatch.setenv("OPENAPI_URL", "")
    monkeypatch.setenv("DATABASE_URL", "   ")
    monkeypatch.setenv("SECRET_KEY", "")

    settings = Settings()
    assert settings.docs_url is None
    assert settings.redoc_url is None
    assert settings.openapi_url is None
    assert settings.database_url is None
    assert settings.secret_key is None


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("app_name", ""),
        ("app_name", "   "),
        ("app_env", "sandbox"),
        ("api_host", ""),
        ("api_host", "   "),
        ("api_port", 0),
        ("api_port", 65536),
        ("api_prefix", "api/v1"),  # Missing leading slash
        ("api_prefix", ""),
        ("log_level", "VERBOSE"),
        ("docs_url", "docs"),  # Missing leading slash
        ("redoc_url", "redoc"),  # Missing leading slash
        ("openapi_url", "openapi.json"),  # Missing leading slash
    ],
)
def test_invalid_settings_raise_validation_error(field: str, invalid_value: object) -> None:
    """Invalid configuration values fail fast with a Pydantic ValidationError."""
    with pytest.raises(ValidationError):
        Settings(**{field: invalid_value})


def test_production_debug_forbidden() -> None:
    """Enabling debug mode in production environment is strictly prevented."""
    # Direct lowercase production
    with pytest.raises(ValidationError, match="debug mode cannot be enabled"):
        Settings(app_env="production", debug=True)

    # Uppercase production normalization
    with pytest.raises(ValidationError, match="debug mode cannot be enabled"):
        Settings(app_env="PRODUCTION", debug=True)

    # Production with debug=False must succeed
    prod_settings = Settings(app_env="production", debug=False)
    assert prod_settings.app_env == "production"
    assert prod_settings.debug is False


def test_openapi_disabled_cascades_to_docs_and_redoc() -> None:
    """Disabling openapi_url automatically suppresses Swagger UI and ReDoc in the app factory."""
    settings = Settings(openapi_url=None, docs_url="/docs", redoc_url="/redoc")
    app = create_app(settings)

    assert app.openapi_url is None
    assert app.docs_url is None
    assert app.redoc_url is None

    client = TestClient(app)
    assert client.get("/openapi.json").status_code == 404
    assert client.get("/docs").status_code == 404
    assert client.get("/redoc").status_code == 404


def test_settings_overrides_create_isolated_applications() -> None:
    """Independent Settings objects produce isolated applications without cross-contamination."""
    app_a = create_app(Settings(app_name="Node Alpha", api_prefix="/api/alpha"))
    app_b = create_app(Settings(app_name="Node Beta", api_prefix="/api/beta"))

    client_a = TestClient(app_a)
    client_b = TestClient(app_b)

    # Verify App A routing and service identity
    resp_a = client_a.get("/api/alpha/health")
    assert resp_a.status_code == 200
    assert resp_a.json()["service"] == "Node Alpha"
    assert client_a.get("/api/beta/health").status_code == 404

    # Verify App B routing and service identity
    resp_b = client_b.get("/api/beta/health")
    assert resp_b.status_code == 200
    assert resp_b.json()["service"] == "Node Beta"
    assert client_b.get("/api/alpha/health").status_code == 404


def test_root_api_prefix_mounting() -> None:
    """Configuring api_prefix='/' mounts endpoints directly at the root."""
    settings = Settings(api_prefix="/")
    app = create_app(settings)
    client = TestClient(app)

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    ready_resp = client.get("/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"


@pytest.mark.parametrize(
    "valid_url",
    [
        "postgresql+psycopg://user:pass@localhost:5432/arogya_ai",
        "postgresql://user:pass@localhost:5432/arogya_ai",
        "postgresql+psycopg2://user:pass@localhost:5432/arogya_ai",
        "postgresql+asyncpg://user:pass@localhost:5432/arogya_ai",
        "postgres://user:pass@localhost/arogya_ai",
        "postgresql://localhost/arogya_ai",
    ],
)
def test_database_url_valid_schemes_accepted(valid_url: str) -> None:
    """Supported PostgreSQL connection URL formats are accepted without error."""
    settings = Settings(database_url=valid_url)
    assert settings.database_url == valid_url


@pytest.mark.parametrize(
    "empty_val",
    ["", "   ", "none", "null", "disabled", None],
)
def test_database_url_empty_values_normalized_to_none(empty_val: str | None) -> None:
    """Empty, whitespace-only, or disabling database URLs normalize cleanly to None."""
    settings = Settings(database_url=empty_val)
    assert settings.database_url is None
    assert settings.masked_database_url is None


@pytest.mark.parametrize(
    ("invalid_url", "expected_match"),
    [
        ("mysql://user:pass@localhost:3306/db", "must use a PostgreSQL scheme"),
        ("sqlite:///local.db", "must use a PostgreSQL scheme"),
        ("mongodb://localhost:27017/db", "must use a PostgreSQL scheme"),
        ("not_a_valid_url", "must use a PostgreSQL scheme"),
        ("postgresql://", "must include a host and database name"),
    ],
)
def test_database_url_invalid_schemes_rejected(invalid_url: str, expected_match: str) -> None:
    """Non-PostgreSQL schemes or malformed URLs raise ValidationError with clear messages."""
    with pytest.raises(ValidationError, match=expected_match):
        Settings(database_url=invalid_url)


def test_database_credentials_not_exposed_in_validation_error() -> None:
    """Validation errors for rejected schemes never echo submitted usernames or passwords."""
    sensitive_user = "secret_clinical_admin"
    sensitive_pass = "SuperSecretDbPassword#99"
    bad_url = f"mysql://{sensitive_user}:{sensitive_pass}@localhost:3306/arogya_db"

    with pytest.raises(ValidationError) as exc_info:
        Settings(database_url=bad_url)

    error_text = str(exc_info.value)
    assert sensitive_user not in error_text
    assert sensitive_pass not in error_text
    assert "mysql" in error_text


def test_masked_database_url_redacts_credentials() -> None:
    """The masked_database_url property replaces passwords with asterisks."""
    full_url = "postgresql+psycopg://clinician:SuperSecretPwd123@db.hospital.local:5432/arogya_prod"
    settings = Settings(database_url=full_url)

    masked = settings.masked_database_url
    assert masked is not None
    assert "SuperSecretPwd123" not in masked
    assert "clinician:***@db.hospital.local:5432/arogya_prod" in masked
    assert masked == "postgresql+psycopg://clinician:***@db.hospital.local:5432/arogya_prod"

    # URL without password
    no_pass_url = "postgresql://localhost:5432/arogya_ai"
    settings_no_pass = Settings(database_url=no_pass_url)
    assert settings_no_pass.masked_database_url == no_pass_url

    # None database URL
    settings_none = Settings(database_url=None)
    assert settings_none.masked_database_url is None


def test_app_creation_with_valid_database_url_does_not_connect() -> None:
    """Configuring a database URL does not initiate a connection on import or app creation."""
    # Use TEST-NET-1 documentation IP (RFC 5737) to guarantee any real connection attempt would fail/hang
    unreachable_url = "postgresql+psycopg://user:pass@192.0.2.1:5432/arogya_test"
    settings = Settings(database_url=unreachable_url)

    # App instantiation must succeed immediately without attempting a socket connection
    app = create_app(settings)
    client = TestClient(app)

    # Health probe succeeds
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"

    # Readiness probe succeeds without attempting connection
    ready_resp = client.get("/api/v1/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"
    assert ready_resp.json()["checks"]["database"]["status"] == "unconfigured"
