# Arogya AI — API Conventions & Architecture Specification

> **Status Notice:** Implemented as of Module 2 (Backend Platform), Phase 2.6.<br/>
> This document specifies the REST API design conventions, schema structures, error-handling contracts, and documentation standards for Arogya AI.
>
> **Implementation Scope Boundary:**
> * **Currently Implemented (Phase 2.6):** FastAPI application factory, runtime settings, versioned route prefixing (`/api/v1`), health (`/health`) and readiness (`/ready`) endpoints, standard error envelopes (`ErrorResponse`), request correlation tracing (`X-Request-ID`), structured logging, and generated OpenAPI 3.1.0 documentation.
> * **Future Architectural Conventions (Modules 3–14):** Resource endpoints for patient records, clinical encounters, tabular ML predictions, chest X-ray vision workflows, and multi-agent coordination are design conventions for upcoming phases and are **not yet implemented**.

---

## 1. API Prefix & Versioning Policy

### Implemented Behavior
* All application domain endpoints are mounted under a versioned API prefix configured via `Settings.api_prefix` (default: `/api/v1`).
* The prefix is applied uniformly in [`backend/app/main.py`](../../backend/app/main.py) during router mounting:
  ```python
  prefix = app_settings.api_prefix.rstrip("/")
  app.include_router(health_router, prefix=prefix)
  ```
* Base infrastructure routes (such as interactive documentation and OpenAPI schema discovery) reside at the root level (`/openapi.json`, `/docs`, `/redoc`) and are configuration-driven.

### Versioning Rules & Evolution
1. **Major Versioning in URL Path:** Breaking changes to existing API contracts require incrementing the major version identifier in the path (e.g., `/api/v1` to `/api/v2`).
2. **Backward-Compatible Minor Changes:** The following additions are non-breaking and do not trigger a major version bump:
   * Adding new endpoints.
   * Adding optional request parameters or optional JSON body attributes.
   * Adding new fields to response payloads.
   * Adding new machine-readable error codes.
3. **Breaking Changes:** The following changes are breaking and require a new API version:
   * Removing or renaming existing endpoints.
   * Removing or renaming existing response attributes.
   * Altering the data type or format of existing response attributes.
   * Adding mandatory (required) fields to existing request payloads.

---

## 2. HTTP Methods, Resource Naming & Status Codes

### Resource Naming Conventions
* **Plural Nouns:** Use plural nouns for REST collection resources (e.g., `/patients`, `/encounters`, `/models`).
* **kebab-case URLs:** Multi-word URI path segments use lowercase alphanumeric characters with hyphens (e.g., `/patient-records`, `/risk-scores`).
* **Action Sub-resources:** When an operation does not map cleanly to standard CRUD verbs (such as executing an ML inference or running an agent pipeline), use a trailing verb on the specific resource (e.g., `POST /api/v1/cases/{case_id}/run-analysis`).

### Supported HTTP Methods

| HTTP Method | Idempotent | Safe | Typical Use Case | Expected Success Status |
| :--- | :---: | :---: | :--- | :--- |
| **`GET`** | Yes | Yes | Retrieve resource representation or execute health probes | `200 OK` |
| **`POST`** | No | No | Create a new entity or trigger a state-transition action | `201 Created` / `200 OK` |
| **`PUT`** | Yes | No | Replace an existing entity completely | `200 OK` |
| **`PATCH`** | No | No | Apply partial updates to an existing entity | `200 OK` |
| **`DELETE`** | Yes | No | Remove an existing entity | `200 OK` / `204 No Content` |

### Standard HTTP Status Codes

| Code | Label | Usage in Arogya AI |
| :--- | :--- | :--- |
| **`200`** | **OK** | Request completed successfully with a response body. |
| **`201`** | **Created** | New resource successfully created (future modules). |
| **`204`** | **No Content** | Request succeeded; no response payload returned. |
| **`400`** | **Bad Request** | Malformed request or semantic domain rule violation. |
| **`401`** | **Unauthorized** | Missing or invalid authentication token (future Module 7). |
| **`403`** | **Forbidden** | Caller lacks role-based permissions for resource (future Module 7). |
| **`404`** | **Not Found** | Targeted route or resource does not exist. |
| **`405`** | **Method Not Allowed** | HTTP method is not supported for the requested route. |
| **`409`** | **Conflict** | Conflicting state (e.g., duplicate unique record). |
| **`422`** | **Unprocessable Entity**| Request payload failed schema validation rules. |
| **`429`** | **Too Many Requests** | Rate limit exceeded (future operational middleware). |
| **`500`** | **Internal Server Error**| Unhandled server exception (internal details shielded). |
| **`503`** | **Service Unavailable** | Critical application component offline or unconfigured. |

---

## 3. JSON Request & Response Conventions

### Data Format & Encoding
* All JSON payloads must be UTF-8 encoded with `Content-Type: application/json`.
* Field names in JSON request and response bodies must adhere to **`snake_case`**.
* Date and timestamp values must adhere to **ISO 8601 UTC** formatted strings (e.g., `2026-10-25T00:00:00Z`).
* Monorepo frontend and backend models share strict contract parity via generated or synchronized Pydantic v2 schemas.

### Response Payload Structure
* **Single Resource:** Return the resource object directly or in a typed response schema (e.g., `HealthResponse`, `ReadyResponse`).
* **Collections (Future):** Paginated collections should return a standardized pagination envelope:
  ```json
  {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 50
  }
  ```

---

## 4. Standard Error Response Envelope

All error responses across Arogya AI are formatted in a standard top-level JSON envelope defined by `ErrorResponse` in [`backend/app/errors.py`](../../backend/app/errors.py).

### Schema Specification
```json
{
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human-readable explanation of the issue.",
    "request_id": "4b68e9e1-6789-4a43-bc8e-28954d72851d",
    "details": [
      {
        "loc": ["body", "field_name"],
        "msg": "Specific validation rule failure description.",
        "type": "string_type"
      }
    ]
  }
}
```

### Stable Error Code Catalog

| Status Code | Standard Error Code | Description |
| :---: | :--- | :--- |
| 400 | `BAD_REQUEST` | General domain rule or syntax violation. |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication token. |
| 403 | `FORBIDDEN` | Insufficient permissions for operation. |
| 404 | `RESOURCE_NOT_FOUND` | Path or entity does not exist. |
| 405 | `METHOD_NOT_ALLOWED` | Unsupported HTTP verb on route. |
| 409 | `CONFLICT` | Concurrent modification or uniqueness violation. |
| 422 | `VALIDATION_ERROR` | Request payload failed schema validation. |
| 429 | `RATE_LIMITED` | Quota or throughput limit exceeded. |
| 500 | `INTERNAL_SERVER_ERROR`| Unhandled server exception. |
| 502 | `BAD_GATEWAY` | Downstream network failure. |
| 503 | `SERVICE_UNAVAILABLE` | Service initialization incomplete or dependency unready. |

### Sanitized Validation Handling (HTTP 422)
When Pydantic request validation fails, FastAPI automatically triggers `validation_exception_handler`.
* **Privacy Guardrail:** The validation handler extracts field locations (`loc`), machine types (`type`), and descriptions (`msg`), but **strictly suppresses raw user input (`input`)**.
* **Clinical Safety Rationale:** Preventing reflection of raw input guarantees that accidentally submitted patient health information (PHI), passwords, or credentials are never leaked into error response bodies.

### Internal Exception Shielding (HTTP 500)
When an unexpected exception occurs:
* Internal stack traces, SQL queries, system paths, and Python exception types are **never** returned to the client.
* Clients receive a generic error: `"An unexpected internal server error occurred."` with code `"INTERNAL_SERVER_ERROR"`.
* The complete traceback is recorded in secure server logs correlated with the `request_id`.

---

## 5. Request Correlation Tracing (`X-Request-ID`)

To maintain end-to-end traceability across distributed services, debugging sessions, and audit logs:

1. **Header Attachment:** Every HTTP response carries the `X-Request-ID` header.
2. **Generation & Ingestion Policy:**
   * If an incoming request includes an `X-Request-ID` header matching the safe alphanumeric pattern (`^[a-zA-Z0-9_\-]{8,64}$`), the client ID is preserved.
   * If the header is missing, malformed, or exceeds bounds, `RequestContextMiddleware` generates a fresh UUID4.
3. **Correlation Binding:**
   * The resolved `request_id` is stored in `request.state.request_id`.
   * It is injected into the standard error envelope (`error.request_id`).
   * It is stored in Python `contextvars` for automatic injection into all structured JSON log records.

---

## 6. Route Registration & Documentation Standards

All future routers must adhere to the following implementation and documentation rules:

### 1. Dedicated Router Modules
* Routers must reside under `backend/app/api/` (e.g., `backend/app/api/patients.py`).
* Routers must define their OpenAPI tag and standard error responses:
  ```python
  from fastapi import APIRouter
  from backend.app.errors import ErrorResponse

  router = APIRouter(
      tags=["Patients"],
      responses={
          500: {
              "model": ErrorResponse,
              "description": "Internal server error response envelope",
          }
      },
  )
  ```

### 2. Mandatory Route Metadata
Every route declaration must explicitly provide:
* **`response_model`:** Typed Pydantic model for response serialization.
* **`status_code`:** Explicit HTTP status code constant.
* **`summary`:** Concise human-readable operation summary (sentence case).
* **`description`:** Detailed description of purpose, invariants, and constraints.
* **`operation_id`:** Explicit, unique machine-readable operation identifier (snake_case, e.g. `get_health`, `create_encounter`).

### 3. Application Factory Registration
* Routers must be mounted in `create_app()` in [`backend/app/main.py`](../../backend/app/main.py):
  ```python
  prefix = app_settings.api_prefix.rstrip("/")
  app.include_router(new_router, prefix=prefix)
  ```
* Any new tags should be registered in `OPENAPI_TAGS` in [`backend/app/main.py`](../../backend/app/main.py) to provide descriptive documentation in Swagger UI.

---

## 7. Interactive Documentation & Schema Access

FastAPI automatically generates an OpenAPI 3.1.0 document from code annotations and Pydantic schemas.

### Default Local Endpoints
* **OpenAPI 3.1 JSON Schema:** `http://127.0.0.1:8000/openapi.json`
* **Swagger UI (Interactive):** `http://127.0.0.1:8000/docs`
* **ReDoc (Reference):** `http://127.0.0.1:8000/redoc`

### Configuration-Driven Documentation
Documentation paths are governed by `Settings` in [`backend/app/settings.py`](../../backend/app/settings.py):
* `openapi_url`: Configures the JSON schema path (`default: "/openapi.json"`).
* `docs_url`: Configures Swagger UI path (`default: "/docs"`).
* `redoc_url`: Configures ReDoc path (`default: "/redoc"`).

Setting any of these fields to `None` (or via environment variables) safely disables the corresponding endpoint, returning a standard 404 error envelope without altering application routing mechanics.

---

## 8. API Contract Testing Requirements

To prevent contract regressions and breaking changes during rapid development:

1. **Test Location:** Contract tests reside under `backend/tests/` (specifically [`backend/tests/test_openapi.py`](../../backend/tests/test_openapi.py)).
2. **Schema Verification:**
   * Verify that `/openapi.json` is reachable and returns HTTP 200.
   * Verify that all mounted paths exist under the configured prefix.
   * Verify HTTP methods, `operation_id`, `summary`, and tags for each operation.
   * Verify that documented response models match actual runtime payloads.
   * Verify that `ErrorResponse` and inner models are documented under `components/schemas`.
3. **Prefix Independence:**
   * Tests must verify that passing a custom `api_prefix` shifts both generated schema paths and runtime routing.
4. **Deterministic & Isolated Execution:**
   * All API contract tests must use `fastapi.testclient.TestClient`.
   * Contract tests must run completely offline without relying on external network services.

---

## 9. Compatibility & Deprecation Strategy

For future lifecycle transitions:

1. **Deprecation Notice:** When an endpoint or parameter is marked for future removal:
   * Mark the route with `deprecated=True` in its FastAPI decorator.
   * Document the planned sunset timeline and replacement route in the description.
   * Return standard `Deprecation` and `Sunset` HTTP response headers.
2. **Grace Period:** Deprecated endpoints will remain functional across at least one minor release cycle before retirement.
3. **Removal:** Outdated endpoints are only removed when transitioning to a new major API version prefix (e.g. `/api/v2`).
