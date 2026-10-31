# Arogya AI — Backend Platform

This directory contains the Python backend service, REST API routers, domain logic, and backend test suites for Arogya AI.

> **Status:** Module 3 (Database Persistence & Data Layer) — Phase 3.7: Database Verification and Backup Strategy (Module 3 Complete).<br/>
> The database foundation includes PostgreSQL engine configuration, session lifecycle dependencies, 8 domain models + association table, 32 Pydantic data contracts, Alembic schema migrations (`98574e91500e`), synthetic development seed data, data access repositories, clinical domain services (`ClinicalService`, `UserService`, `AuditService`), read-only database verification (`scripts/verify_database.py`), logical PostgreSQL backups (`scripts/backup_database.py`), and safe disaster recovery procedures (`scripts/restore_database.py`). Architecture details: [`docs/architecture/CONFIGURATION.md`](../docs/architecture/CONFIGURATION.md) and [`docs/architecture/API_DATA_CONTRACTS.md`](../docs/architecture/API_DATA_CONTRACTS.md).

---

## 1. Selected Python Environment & Dependencies

* **Interpreter Version:** Python 3.14.6 (64-bit on Windows).
* **Virtual Environment Path:** `.venv/` (located at repository root, excluded from Git).
* **Core & Testing Dependencies (`backend/requirements.txt`):**
  * `fastapi>=0.115.0,<1.0.0`
  * `uvicorn[standard]>=0.32.0,<1.0.0`
  * `pydantic-settings>=2.6.0,<3.0.0`
  * `pytest>=8.0.0,<10.0.0`
  * `httpx>=0.27.0,<1.0.0`
  * `sqlalchemy>=2.0.0,<3.0.0`
  * `psycopg[binary]>=3.2.0,<4.0.0`
  * `alembic>=1.13.0,<2.0.0`

### Installing Dependencies into `.venv`
```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

---

## 2. Local Execution & Automation Scripts

A dedicated PowerShell runner ([`scripts/run_backend.ps1`](../scripts/run_backend.ps1)) automates local development server startup and test execution using the isolated `.venv` interpreter:

### Starting the Local Development Server
From the repository root (`C:\_code\Projects\Arogya-AI`):

```powershell
.\scripts\run_backend.ps1
```

By default, the server binds to localhost loopback (`127.0.0.1:8000`) with auto-reload enabled.

#### Optional CLI Flags:
* **Custom Port:** `.\scripts\run_backend.ps1 -Port 8080`
* **Disable Reload:** `.\scripts\run_backend.ps1 -NoReload`
* **Run Tests:** `.\scripts\run_backend.ps1 -Test`

### Interactive API Documentation & OpenAPI Schema
Once running, OpenAPI documentation is available at:
* OpenAPI 3.1 JSON Schema: `http://127.0.0.1:8000/openapi.json`
* Swagger UI (Interactive Explorer): `http://127.0.0.1:8000/docs`
* ReDoc (API Reference): `http://127.0.0.1:8000/redoc`

#### Inspecting OpenAPI Schema via Command Line
To inspect the generated OpenAPI JSON schema without starting the HTTP server:
```powershell
.\.venv\Scripts\python.exe -c "import json; from backend.app.main import create_app; print(json.dumps(create_app().openapi(), indent=2))"
```

#### Disabling Documentation Routes in Staging or Production
In production, interactive documentation can be disabled via environment variables:
* Set `OPENAPI_URL=none`, `DOCS_URL=none`, or `REDOC_URL=none` (or empty strings in `.env`).
* Disabling `OPENAPI_URL` automatically cascades to suppress both Swagger UI and ReDoc.
* *Security Notice:* Disabling documentation is an operational hygiene control; it does **not** replace authentication, network authorization, or access control. Reference: [`docs/architecture/CONFIGURATION.md`](../docs/architecture/CONFIGURATION.md).

### Manual Shell Activation (Optional)
```powershell
.\.venv\Scripts\Activate.ps1
```

---

## 3. Standard Error Envelopes

All HTTP errors, schema validation failures, and unhandled exceptions are caught and formatted into a consistent, safe JSON envelope:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Not Found",
    "request_id": "4b68e9e1-6789-4a43-bc8e-28954d72851d"
  }
}
```

### Sanitized Validation Failures (HTTP 422)
When request payload validation fails, field locations and rule violations are returned, but **raw user input is strictly dropped** to prevent leaking sensitive medical values, passwords, or PHI:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted request payload failed schema validation.",
    "request_id": "4b68e9e1-6789-4a43-bc8e-28954d72851d",
    "details": [
      {
        "loc": ["body", "patient_age"],
        "msg": "Input should be a valid integer",
        "type": "int_parsing"
      }
    ]
  }
}
```

### Unhandled Server Exceptions (HTTP 500)
Internal exceptions return a generic message (`"An unexpected internal server error occurred."`) without leaking stack traces, database credentials, or file paths. The full exception trace is recorded internally in server logs correlated with the `request_id`.

---

## 4. Request IDs & Correlation Tracing

* **Generation:** Every incoming request is assigned a unique UUID4 by `RequestContextMiddleware`.
* **Client Preservation Policy:** If an incoming `X-Request-ID` header matches a safe alphanumeric pattern (`^[a-zA-Z0-9_\-]{8,64}$`), it is preserved for distributed tracing. Malformed or unsafe headers are rejected and replaced with a fresh UUID.
* **Propagation:** The correlation ID is attached to:
  * Outgoing `X-Request-ID` HTTP response headers.
  * The `error.request_id` field in all error envelopes.
  * Asynchronous `contextvars` for automatic injection into log records.

---

## 5. Structured Logging & Operational Privacy

Application logging is configured via standard Python `logging` (`backend/app/logging.py`) without third-party frameworks:
* **Format:** Single-line structured JSON records containing UTC ISO 8601 timestamps, severity level, logger name, message, and correlation `request_id`.
* **Privacy Guardrails:** Loggers record HTTP method, path, status, and duration, but **never** record request bodies, query values, authorization headers, cookies, or patient-identifiable data.
* **Scope Notice:** Logs and request correlation IDs are operational debugging metadata; they do not imply HIPAA/GDPR clinical compliance or security certification.

---

---

## 6. Database Persistence, Engine Lifecycle & Session Management

As of Module 3, Phase 3.3, database persistence and domain models are established under `backend/app/db/`:

### Architecture & Components
* **Declarative Base (`backend/app/db/base.py`):**
  * Defines SQLAlchemy 2.x `Base` (`DeclarativeBase`) and exposes `metadata`.
* **Clinical Domain Models (`backend/app/db/models.py`):**
  * Implements 8 initial domain entities + 1 association table: `User`, `Role`, `user_roles`, `Patient`, `Encounter`, `Observation`, `UploadedAsset`, `AnalysisRun`, and `AuditEvent`.
  * Utilizes portable types (`Uuid`, `DateTime(timezone=True)`, `JSON`).
  * Enforces strict referential deletion rules (`RESTRICT` on clinical history, `SET NULL` on audit actor and asset links).
  * Segregates ground-truth observations from probabilistic AI outputs.
* **Synchronous Engine (`create_db_engine`):**
  * Configures connection pooling defaults: `pool_pre_ping=True`, `pool_size=5`, `max_overflow=10`, `pool_timeout=30.0`, `pool_recycle=1800`, and a bounded driver connection timeout (`connect_timeout=10`).
  * Lazily initializes connections; engine construction or application factory startup **never initiates an immediate network connection**.
  * Caches a process-level engine singleton (`get_engine`) and supports clean teardown (`dispose_engine`).
* **Session Lifecycle (`get_db_session`):**
  * Provides a FastAPI dependency yielding an isolated `Session` per HTTP request.
  * Ensures deterministic cleanup via `try...finally`: commits are handled explicitly by business handlers, unhandled exceptions trigger `session.rollback()`, and `session.close()` is guaranteed upon request exit.
  * Sessions are strictly request-scoped and never shared across concurrent requests.
* **Connection Verification (`check_database_connection`):**
  * Performs a lightweight probe query (`SELECT 1`) to test live connectivity.
  * Releases acquired connections back to the pool immediately.
  * Catches driver failures and raises `DatabaseConnectionError` while preserving the underlying cause for debugging; **connection credentials and passwords are never exposed in error text or logs**.

### Safe Local Development & Startup Rules
* **No Startup Migrations or Table Creation:** Application startup (`create_app()`) strictly **must not** run `Base.metadata.create_all()` or Alembic migrations automatically. Automatic DDL on startup creates operational race conditions in clustered deployments and risks silent schema desynchronization.
* **Schema Evolution:** Managed explicitly via Alembic migrations starting in Phase 3.5.

### Testing Strategy: SQLite In-Memory vs. PostgreSQL
* **Isolated Unit Testing:** Backend unit tests use in-memory SQLite engines (`sqlite:///:memory:`) with `StaticPool` to verify dialect-independent session mechanics, rollback behavior, and FastAPI dependency wiring without external infrastructure.
* **PostgreSQL Incompatibility Notice:** **SQLite test passes do NOT establish PostgreSQL production compatibility.** SQLite lacks PostgreSQL-specific types (`UUID`, `JSONB`, `ARRAY`), specific dialect constraints, transactional DDL semantics, and connection concurrency characteristics.
* **PostgreSQL Integration Testing:** Requires a dedicated PostgreSQL 18 instance with application credentials configured in `.env`. Integration testing against live databases remains decoupled from local unit test runs.

---

## 7. Running Backend Tests

Backend tests are organized with root-level [`pytest.ini`](../pytest.ini) and shared fixtures in [`backend/tests/conftest.py`](tests/conftest.py):

### Executing Tests via Automation Script
```powershell
.\scripts\run_backend.ps1 -Test
```

### Direct Pytest Invocation
```powershell
.\.venv\Scripts\python.exe -m pytest
```

### Running Database & Model Tests Exclusively
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_database.py backend/tests/test_models.py -v
```

### Running Schema & Data Contract Tests Exclusively
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_schemas.py -v
```

### Running Migration & Seed Tests Exclusively
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_migrations.py backend/tests/test_seed.py -v
```

### Running Repository & Domain Service Tests Exclusively
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests/test_repositories.py backend/tests/test_services.py -v
```

### Test Scope & Coverage:
* Data access repositories (User, Role, Patient, Encounter, Observation, UploadedAsset, AnalysisRun, AuditEvent) with CRUD operations, eager loading, and `None` returns for missing entities.
* Repository bounded pagination sanitization clamping limit (1–500) and offset (>=0).
* Domain services (`ClinicalService`, `UserService`, `AuditService`) managing business workflows and relational invariants.
* Patient-Encounter-Observation ownership validation raising typed `ConsistencyError` on patient mismatches.
* Asset and AnalysisRun cross-entity alignment raising `ConsistencyError` on invalid patient/encounter associations.
* Pseudonymous MRN alias mapping (`mrn` ↔ `mrn_pseudonym`) via Pydantic `AliasChoices` without changing database schema.
* Natural key uniqueness enforcement raising typed `DuplicateEntityError` (username, email, MRN, storage path).
* Missing entity reference validation raising typed `EntityNotFoundError`.
* Caller-owned transaction atomicity: verifying full rollback of multi-entity operations when exceptions occur.
* Operational audit logging with automated credential redaction (`password`, `hashed_password`, `secret_key`, `token`).
* Alembic migration configuration, script directory, and versions path resolution.
* Target metadata validation registering all 9 healthcare entities and association tables in `Base.metadata`.
* Initial migration revision (`98574e91500e`) schema parity: creation and dropping of all 9 tables.
* Cascade referential actions on association tables, RESTRICT policies protecting historical patient records, and SET NULL on audit/asset links.
* Offline PostgreSQL DDL generation without requiring a live database connection (`alembic upgrade head --sql`).
* Seed environment safety guard refusing execution in `production`, `prod`, `staging`, and `live`.
* CLI opt-in enforcement requiring `--confirm-dev-seed`.
* Deterministic seed record generation and strict idempotency (0 new records on second run).
* Transactional rollback verification ensuring failures leave no partial records.
* Seed data governance: zero-PHI synthetic patient MRNs, locked account password sentinels, and demo AI output disclaimers.
* Pydantic v2 request/response contracts for User, Role, Patient, Encounter, Observation, UploadedAsset, AnalysisRun, and AuditEvent domains.
* Strict input validation with `extra="forbid"` to reject unexpected, undocumented client fields.
* Automatic string whitespace stripping on all incoming payload fields.
* Timezone awareness enforcement requiring UTC offsets on timestamps; rejection of naive datetimes.
* Exclusion of sensitive attributes (`hashed_password`, internal storage paths, server-generated timestamps) from response and request contracts.
* Prevention of client-injected trusted AI analysis outputs, statuses, and completed timestamps upon run creation.
* Prevention of client-injected internal file storage paths on uploaded asset metadata creation.
* Asset checksum format validation (SHA-256 64-character lowercase hexadecimal regex) and strictly positive byte size constraints.
* Observation value integrity: enforcement that at least one of `numeric_value` or `text_value` is populated.
* Encounter temporal order integrity: validation that `end_time >= start_time`.
* ORM serialization parity: verifying `from_attributes=True` serialization from representative SQLAlchemy domain entities.
* Declarative base export, MetaData collection, and table registration.
* Entity mappings for 8 clinical domain tables + 1 explicit association table: `users`, `roles`, `user_roles`, `patients`, `encounters`, `observations`, `uploaded_assets`, `analysis_runs`, `audit_events`.
* Primary keys (`Uuid`) and foreign key relationships with referential deletion policies (`RESTRICT` on clinical history, `SET NULL` on audit actors and asset links).
* Uniqueness constraints across usernames, emails, role names, pseudonymous MRNs, and storage paths.
* Many-to-Many user-role association mechanics and cascade behavior.
* Patient-Encounter-Observation hierarchy with distinct numeric vs. text observation values.
* UploadedAsset metadata tracking (with checksums and file sizes) and AnalysisRun model output segregation.
* AuditEvent operational logging, actor linkages, and privacy safeguards (zero PHI/credentials).
* Timezone-aware timestamp defaults and non-nullable field constraints.
* Foreign-key constraint enforcement via SQLite `PRAGMA foreign_keys=ON`.
* Engine construction laziness, driver scheme validation, and URL normalization (`postgresql+psycopg://`).
* Rejection of incompatible asynchronous (`asyncpg`) and legacy (`psycopg2`) drivers.
* Engine singleton caching and deterministic teardown (`dispose_engine`).
* Session query execution on dialect-independent test engines.
* Session dependency lifecycle: deterministic closure, automatic rollback on exception, and FastAPI dependency injection.
* Connection verification probe (`SELECT 1`), failure handling, and credential masking.
* Liveness (`/health`) and readiness (`/ready`) response contracts.
* Error envelope formatting across 404, 422, and 500 status codes.
* Field location extraction without echoing sensitive input values.
* Sanitization of 500 errors to prevent leaking internal exception text.
* Uniqueness, preservation, and replacement of `X-Request-ID` headers.
* Dynamic prefix routing and nonexistent route handling.
* OpenAPI 3.1.0 schema retrieval, route documentation, operation IDs, and tags.
* Component schema registration (`HealthResponse`, `ReadyResponse`, `ErrorResponse`, etc.).
* Runtime response payload alignment against OpenAPI component schemas.
* Custom API prefix adaptation in generated schema and runtime routing.
* Configuration-driven interactive docs enabling and disabling (`/docs`, `/redoc`, `/openapi.json`).
* Settings validation, environment variable parsing, case normalization, and port bounds checking.
* Production debug mode prevention and configuration isolation across application instances.

---

## 8. Operational Readiness vs. Clinical Readiness

> **Important Boundary Notice:**<br/>
> The local development server and automated tests verify **software engineering mechanics only** (HTTP lifecycle, routing, error envelopes, logging, database session lifecycles, and Pydantic validation contracts). This does **not** constitute clinical validation, medical device certification, or production deployment readiness. External databases (Module 3), multi-agent pipelines (Module 11), and clinical safety controls (Module 13) are introduced in subsequent modules.

---

## 9. Directory Layout

```text
Arogya-AI/
├── pytest.ini           # Root pytest test runner configuration
├── scripts/
│   ├── backup_database.ps1    # PowerShell wrapper for PostgreSQL backup
│   ├── backup_database.py     # Logical custom-format backup (pg_dump) with credential protection
│   ├── restore_database.ps1   # PowerShell wrapper for restore & verification
│   ├── restore_database.py    # Safe restore into disposable target (pg_restore)
│   ├── run_backend.ps1        # Local development server and test automation
│   ├── seed_dev_data.py       # Idempotent synthetic development seed data generator
│   ├── validate_foundation.ps1
│   └── verify_database.py     # Non-destructive database connectivity & schema verifier
└── backend/
    ├── alembic.ini      # Alembic migration configuration
    ├── alembic/         # Alembic migration environment and versions
    │   ├── env.py       # Migration runner (binds Base.metadata and resolves DB URL)
    │   ├── script.py.mako # Migration template
    │   └── versions/
    │       └── 98574e91500e_initial_schema.py # Initial healthcare domain migration
    ├── app/
    │   ├── __init__.py  # Package exports (create_app, Settings, Error models)
    │   ├── main.py      # Application factory, middleware, and router registration
    │   ├── settings.py  # Validated Pydantic settings model
    │   ├── errors.py    # Standard error envelope and exception handlers
    │   ├── logging.py   # Structured JSON logging and contextvar tracking
    │   ├── middleware.py# RequestContextMiddleware for X-Request-ID tracing
    │   ├── api/
    │   │   ├── __init__.py
    │   │   └── health.py# /health and /ready probe implementations
    │   ├── db/
    │   │   ├── __init__.py  # Database package exports (engine, session, models)
    │   │   ├── base.py      # SQLAlchemy 2.x declarative base and metadata
    │   │   ├── models.py    # Initial healthcare domain entities & user_roles
    │   │   └── session.py   # Engine, session factory, dependency, and connection check
    │   ├── repositories/# Data access repositories (SQLAlchemy queries & CRUD)
    │   │   ├── __init__.py
    │   │   ├── base.py      # BaseRepository with pagination sanitization
    │   │   ├── user.py      # UserRepository and RoleRepository
    │   │   ├── patient.py   # PatientRepository with MRN lookup
    │   │   ├── encounter.py # EncounterRepository
    │   │   ├── observation.py # ObservationRepository
    │   │   ├── asset.py     # AssetRepository
    │   │   ├── analysis.py  # AnalysisRepository
    │   │   └── audit.py     # AuditRepository (immutable append-only)
    │   ├── services/    # Clinical domain services & business logic
    │   │   ├── __init__.py
    │   │   ├── exceptions.py# Typed domain exceptions (EntityNotFound, ConsistencyError)
    │   │   ├── clinical.py  # ClinicalService (patient, encounter, obs, asset, analysis)
    │   │   ├── user.py      # UserService (user lifecycle, role assignments)
    │   │   └── audit.py     # AuditService (credential-scrubbed audit logging)
    │   └── schemas/     # Pydantic v2 API data contracts & serialization schemas
    │       ├── __init__.py  # Schema package exports (32 symbols)
    │       ├── common.py    # BaseSchema, ORMModel, PaginatedResponse, timezone validators
    │       ├── user.py      # User and Role request/response contracts
    │       ├── patient.py   # Pseudonymous Patient request/response contracts
    │       ├── encounter.py # Clinical Encounter request/response contracts
    │       ├── observation.py # Clinical Observation request/response contracts
    │       ├── asset.py     # Uploaded asset metadata contracts
    │       ├── analysis.py  # AnalysisRun creation and response contracts
    │       └── audit.py     # Read-only audit event response and filter contracts
    ├── tests/
    │   ├── __init__.py  # Backend test package
    │   ├── conftest.py  # Shared pytest fixtures (app, client, test_settings)
    │   ├── test_database.py               # Database engine, session lifecycle, and probe tests
    │   ├── test_models.py                 # Clinical domain entities & relationship tests
    │   ├── test_schemas.py                # Pydantic contract validation & serialization tests
    │   ├── test_migrations.py             # Alembic configuration & schema migration tests
    │   ├── test_seed.py                   # Synthetic development seed data tests
    │   ├── test_repositories.py           # Data access repository unit tests
    │   ├── test_services.py               # Clinical domain services & consistency tests
    │   ├── test_verification_and_backup.py# Database verification, backup, & restore tests
    │   ├── test_health.py
    │   ├── test_errors.py
    │   ├── test_openapi.py                # OpenAPI schema & contract regression tests
    │   └── test_settings.py               # Settings validation & runtime hardening tests
    ├── requirements.txt # Pinned core backend and testing dependencies
    └── README.md        # Backend developer guide and setup notes
```

---

## 10. Roadmap Status & Deferred Features

* **Module 2 (Completed):** Backend platform, application factory, health probes, error envelopes, logging, contract tests, and runtime hardening.
* **Phase 3.1 (Completed):** PostgreSQL connection configuration, URI validation, credential masking, and environment safety controls.
* **Phase 3.2 (Completed):** SQLAlchemy 2.0 declarative base, synchronous engine lifecycle, session dependency injection, and connection verification.
* **Phase 3.3 (Completed):** Domain entities and relational data models (User, Role, Patient, Encounter, Observation, UploadedAsset, AnalysisRun, AuditEvent).
* **Phase 3.4 (Completed):** Pydantic API data contracts, validation rules, sensitive field shielding, and serialization schemas.
* **Phase 3.5 (Completed):** Alembic migrations, database schema revision tree (`98574e91500e`), offline PostgreSQL DDL generation, and synthetic development seed data generator.
* **Phase 3.6 (Completed):** Data access repositories, clinical domain service layer, cross-entity consistency enforcement, MRN alias mapping, and credential-sanitized audit logging.
* **Phase 3.7 (Completed):** Database verification utility, logical custom-format PostgreSQL backups (`pg_dump`), safe restore procedures (`pg_restore`), disposable target safety guards, and operational recovery documentation. *(Module 3 Complete)*.

---

## 11. Development Principles & Guardrails

* **Zero Patient Data Policy:** Real patient health information (PHI) must **never** be placed in this directory or used in test fixtures.
* **Secrets Management:** Credentials, database passwords, and API keys must remain strictly in untracked local `.env` files; never commit secrets to version control.
