"""Arogya AI - OpenAPI & API Contract Regression Tests.

Verifies generated OpenAPI 3.x schema, route registrations, metadata,
response models, custom prefix routing, documentation routes, and error envelopes.
"""

from fastapi.testclient import TestClient
from backend.app.main import create_app
from backend.app.settings import Settings


def test_openapi_schema_retrieval(client: TestClient) -> None:
    """OpenAPI JSON document is retrievable and conforms to basic OpenAPI 3 structure."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]

    schema = response.json()
    assert "openapi" in schema
    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == "Arogya AI"
    assert schema["info"]["version"] == "0.1.0"
    assert "paths" in schema
    assert "components" in schema
    assert "tags" in schema


def test_openapi_paths_and_operations(client: TestClient) -> None:
    """Schema documents health and readiness endpoints with proper methods and tags."""
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    assert "/api/v1/health" in paths
    assert "/api/v1/ready" in paths

    health_op = paths["/api/v1/health"]["get"]
    assert health_op["operationId"] == "get_health"
    assert health_op["summary"] == "Liveness Probe"
    assert "alive" in health_op["description"].lower()
    assert "Health" in health_op["tags"]

    ready_op = paths["/api/v1/ready"]["get"]
    assert ready_op["operationId"] == "get_readiness"
    assert ready_op["summary"] == "Readiness Probe"
    assert "ready" in ready_op["description"].lower()
    assert "Health" in ready_op["tags"]


def test_openapi_response_models_and_schemas(client: TestClient) -> None:
    """Schema documents both success models and standard ErrorResponse envelopes."""
    schema = client.get("/openapi.json").json()
    schemas = schema["components"]["schemas"]

    # Verify all expected model definitions exist in components
    assert "HealthResponse" in schemas
    assert "ReadyResponse" in schemas
    assert "ReadyComponentStatus" in schemas
    assert "ErrorResponse" in schemas
    assert "ErrorPayload" in schemas
    assert "ErrorFieldDetail" in schemas

    # Verify endpoint response mappings
    health_responses = schema["paths"]["/api/v1/health"]["get"]["responses"]
    assert "200" in health_responses
    assert "500" in health_responses
    assert (
        health_responses["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/HealthResponse"
    )
    assert (
        health_responses["500"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ErrorResponse"
    )

    ready_responses = schema["paths"]["/api/v1/ready"]["get"]["responses"]
    assert "200" in ready_responses
    assert "500" in ready_responses
    assert (
        ready_responses["200"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ReadyResponse"
    )
    assert (
        ready_responses["500"]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ErrorResponse"
    )


def test_runtime_payloads_satisfy_openapi_schema(client: TestClient) -> None:
    """Runtime response payloads match documented schemas for health and readiness."""
    # Health runtime check
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert set(health_data.keys()) == {"status", "service"}
    assert health_data["status"] == "ok"
    assert health_data["service"] == "Arogya AI"

    # Readiness runtime check
    ready_resp = client.get("/api/v1/ready")
    assert ready_resp.status_code == 200
    ready_data = ready_resp.json()
    assert set(ready_data.keys()) == {"status", "service", "environment", "checks"}
    assert ready_data["status"] == "ready"
    assert isinstance(ready_data["checks"], dict)
    assert "core_api" in ready_data["checks"]
    for check_name, check_info in ready_data["checks"].items():
        assert "status" in check_info
        assert "detail" in check_info
        assert check_info["status"] in ("ready", "not_ready", "unconfigured")


def test_openapi_custom_prefix_adaptation() -> None:
    """Configuring a custom API prefix shifts both generated schema paths and runtime routes."""
    custom_prefix = "/api/v2"
    custom_settings = Settings(
        app_name="Arogya AI",
        app_env="testing",
        debug=False,
        api_prefix=custom_prefix,
    )
    custom_app = create_app(custom_settings)
    custom_client = TestClient(custom_app)

    schema = custom_client.get("/openapi.json").json()
    assert "/api/v2/health" in schema["paths"]
    assert "/api/v2/ready" in schema["paths"]
    assert "/api/v1/health" not in schema["paths"]

    # Verify runtime routing aligns with custom prefix
    resp_v2 = custom_client.get("/api/v2/health")
    assert resp_v2.status_code == 200
    assert resp_v2.json()["status"] == "ok"

    resp_v1 = custom_client.get("/api/v1/health")
    assert resp_v1.status_code == 404
    assert resp_v1.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_interactive_docs_endpoints(client: TestClient) -> None:
    """Swagger UI and ReDoc endpoints are accessible by default."""
    docs_resp = client.get("/docs")
    assert docs_resp.status_code == 200
    assert "text/html" in docs_resp.headers["content-type"]

    redoc_resp = client.get("/redoc")
    assert redoc_resp.status_code == 200
    assert "text/html" in redoc_resp.headers["content-type"]


def test_documentation_routes_configurable_and_disableable() -> None:
    """Documentation endpoints can be disabled via Settings string tokens, returning standard 404s."""
    disabled_settings = Settings(
        app_name="Arogya AI",
        app_env="testing",
        debug=False,
        docs_url="none",
        redoc_url="disabled",
        openapi_url="",
    )
    app = create_app(disabled_settings)
    client = TestClient(app)

    for route in ["/docs", "/redoc", "/openapi.json"]:
        resp = client.get(route)
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_openapi_request_id_and_correlation(client: TestClient) -> None:
    """Schema retrieval and routing errors include X-Request-ID correlation headers."""
    # OpenAPI route contains X-Request-ID
    schema_resp = client.get("/openapi.json")
    assert "X-Request-ID" in schema_resp.headers

    # Preserved correlation ID on docs route
    custom_id = "test-corr-openapi-001"
    docs_resp = client.get("/docs", headers={"X-Request-ID": custom_id})
    assert docs_resp.headers.get("X-Request-ID") == custom_id
