"""Arogya AI - Error Handling, Validation, and Request-ID Tracing Tests.

Validates:
- Standard error envelope formatting across 404, 422, and 500 status codes.
- Sanitized validation details that avoid echoing sensitive inputs.
- Omission of internal exception messages and stack traces on 500 errors.
- Generation and propagation of correlation X-Request-ID headers and payloads.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field


class SamplePayload(BaseModel):
    """Test model for payload validation testing."""

    patient_age: int = Field(gt=0, lt=150)
    session_token: str


@pytest.mark.unit
def test_404_error_envelope(client: TestClient):
    """Verify nonexistent paths return HTTP 404 with standard error envelope."""
    response = client.get("/api/v1/not-a-real-endpoint")
    assert response.status_code == 404
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "not found" in data["error"]["message"].lower()
    assert "request_id" in data["error"]
    assert response.headers.get("X-Request-ID") == data["error"]["request_id"]


@pytest.mark.unit
def test_422_validation_error_envelope_sanitized(app: FastAPI):
    """Verify validation errors return HTTP 422 with location info and without echoing sensitive values."""
    # Mount temporary route for payload validation verification
    @app.post("/test-validation")
    async def temp_validation_endpoint(payload: SamplePayload):
        return {"status": "ok"}

    client = TestClient(app)
    sensitive_value = "VERY_SECRET_PATIENT_PASSWORD_123"
    response = client.post(
        "/test-validation",
        json={
            "patient_age": "not-an-integer",
            "session_token": sensitive_value,
        },
    )

    assert response.status_code == 422
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    assert len(data["error"]["details"]) > 0

    # Ensure field location is reported
    field_locs = [d["loc"] for d in data["error"]["details"]]
    assert any("patient_age" in loc for loc in field_locs)

    # Critical security check: Ensure the sensitive input value is NOT echoed in the response
    assert sensitive_value not in response.text

    # Verify correlation ID consistency
    assert response.headers.get("X-Request-ID") == data["error"]["request_id"]


@pytest.mark.unit
def test_500_internal_server_error_sanitized(app: FastAPI):
    """Verify unexpected server errors return HTTP 500 without leaking exception details."""
    sensitive_exception_text = "DATABASE_PASSWORD_LEAK_SECRET_12345"

    # Mount temporary route that triggers an unhandled exception
    @app.get("/test-unhandled-error")
    async def temp_failing_endpoint():
        raise RuntimeError(sensitive_exception_text)

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-unhandled-error")

    assert response.status_code == 500
    data = response.json()

    assert "error" in data
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert data["error"]["message"] == "An unexpected internal server error occurred."
    assert sensitive_exception_text not in response.text
    assert response.headers.get("X-Request-ID") == data["error"]["request_id"]


@pytest.mark.unit
def test_request_id_generation_and_uniqueness(client: TestClient):
    """Verify each request receives a unique X-Request-ID header."""
    resp1 = client.get("/api/v1/health")
    resp2 = client.get("/api/v1/health")

    id1 = resp1.headers.get("X-Request-ID")
    id2 = resp2.headers.get("X-Request-ID")

    assert id1 is not None and len(id1) >= 16
    assert id2 is not None and len(id2) >= 16
    assert id1 != id2


@pytest.mark.unit
def test_client_provided_valid_request_id(client: TestClient):
    """Verify trusted client-provided X-Request-ID headers are preserved."""
    custom_id = "client-trace-id-abc12345"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


@pytest.mark.unit
def test_client_provided_invalid_request_id_replaced(client: TestClient):
    """Verify malformed or unsafe client request IDs are rejected and replaced."""
    unsafe_id = "<script>alert('xss')</script>"
    response = client.get("/api/v1/health", headers={"X-Request-ID": unsafe_id})

    assert response.status_code == 200
    assigned_id = response.headers.get("X-Request-ID")
    assert assigned_id != unsafe_id
    assert len(assigned_id) == 36  # Standard UUID4 length
