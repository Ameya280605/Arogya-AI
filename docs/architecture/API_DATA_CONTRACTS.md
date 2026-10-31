# Arogya AI — API Data Contracts & Schema Architecture

> **Status Notice:** Implemented as of Module 3 (Database Persistence & Data Layer), Phase 3.4.<br/>
> This document specifies the decoupled Pydantic request and response schemas, validation rules, sensitive-field exclusion policies, and serialization conventions for Arogya AI.
>
> **Implementation Scope Boundary:**
> * **Active Schemas:** Pydantic v2 data contracts under [`backend/app/schemas/`](../../backend/app/schemas/) for User, Role, Patient, Encounter, Observation, UploadedAsset, AnalysisRun, AuditEvent, and common pagination.
> * **Deferred Functionality:** Database migrations and seeds (Phase 3.5), domain repositories and services (Phase 3.6), backup/recovery procedures (Phase 3.7), and CRUD route handlers (Phase 3.6+).

---

## 1. Architectural Separation: Persistence Models vs. API Schemas

A fundamental architectural principle of Arogya AI is the strict decoupling of **SQLAlchemy persistence models** from **Pydantic API contracts**:

```text
  ┌───────────────────────────────────────────────────────────────┐
  │                        Client / UI                            │
  └───────────────────────────────┬───────────────────────────────┘
                                  │ HTTPS JSON Payloads
                                  ▼
  ┌───────────────────────────────────────────────────────────────┐
  │                    Pydantic API Contracts                     │
  │                   (backend/app/schemas/)                      │
  │  - Enforces input validation, field bounds, & extra="forbid"  │
  │  - Shields internal database columns and security secrets     │
  │  - Serializes responses via ConfigDict(from_attributes=True)   │
  └───────────────────────────────┬───────────────────────────────┘
                                  │ Service Layer Mediation (Phase 3.6)
                                  ▼
  ┌───────────────────────────────────────────────────────────────┐
  │                  SQLAlchemy Domain Entities                   │
  │                     (backend/app/db/models.py)                │
  │  - Manages relational tables, foreign keys, & DB indices      │
  │  - Enforces relational referential integrity (RESTRICT, etc.) │
  │  - Persists database-specific types (e.g. hashed_password)    │
  └───────────────────────────────────────────────────────────────┘
```

### Why Decoupling is Essential
1. **Security & Data Hiding:** Database models contain internal or sensitive attributes (e.g., `hashed_password`, internal filesystem `storage_path`, server-assigned timestamps). Exposing database models directly in API endpoints risks catastrophic data leakage.
2. **Independent Evolution:** Database table structures and API contracts evolve at different velocities. Decoupling allows refactoring database tables (e.g. normalization, partitioning) without breaking public API contracts.
3. **Payload Sanitization:** API request models validate and sanitize external user input prior to business logic execution, forbidding unknown fields (`extra="forbid"`) to prevent parameter injection attacks.

---

## 2. Naming Conventions & Schema Taxonomy

Arogya AI adopts standard schema suffixes across all domain entities:

| Schema Suffix | Base Class | Configuration | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **`*Create`** | `BaseSchema` | `extra="forbid"` | Validates client payloads for resource creation. Excludes server-generated identifiers (`id`), timestamps (`created_at`), and internal references. |
| **`*Update`** | `BaseSchema` | `extra="forbid"` | Validates client payloads for partial/full updates. All attributes are optional (`None` default) to support PATCH semantics. |
| **`*Response`** | `ORMModel` | `from_attributes=True` | Formats server responses. Safely maps from SQLAlchemy ORM instances, automatically serializing UUIDs, ISO 8601 UTC datetimes, and nested associations. |
| **`*Filter`** | `BaseSchema` | `extra="forbid"` | Validates query parameters for search, filtering, and range queries (e.g., `AuditEventFilter`). |

---

## 3. Serialization & Validation Conventions

### UUID & Timezone-Aware Timestamps
* **UUID Identifiers:** All primary keys and foreign keys are represented as Python `uuid.UUID` objects in Pydantic schemas. In JSON responses, Pydantic v2 automatically serializes UUIDs as standard 36-character hyphenated strings (`"123e4567-e89b-12d3-a456-426614174000"`).
* **ISO 8601 UTC Timestamps:** All event and lifecycle timestamps are validated for timezone awareness (`ensure_timezone_aware`). Naive datetimes (lacking timezone information) are strictly rejected with HTTP 422 validation errors. Timestamps serialize to ISO 8601 UTC strings (e.g. `"2026-10-25T10:00:00Z"`).

### Unknown Field Handling (`extra="forbid"`)
All request schemas inherit from `BaseSchema`, which enforces `model_config = ConfigDict(extra="forbid")`. Passing unexpected attributes (e.g. client passing `{"is_admin": true}` or `{"storage_path": "/etc/passwd"}`) triggers an immediate `ValidationError`.

### Standard Pagination Envelope
Collection endpoints return data wrapped in `PaginatedResponse[T]`:
```json
{
  "items": [],
  "total": 150,
  "page": 1,
  "page_size": 20
}
```

---

## 4. Sensitive Field Exclusion & Security Boundaries

### User & Authentication Credentials
* **Plaintext Password Handling:** `UserCreate` accepts a `password` field (min 8, max 128 chars) strictly for credential generation upon registration.
* **Response Exclusion:** `UserResponse` **never** defines or outputs `password` or `hashed_password`. Even when serializing directly from an ORM `User` instance populated with a password hash, the hash is dropped by design during Pydantic attribute selection.

### Uploaded Asset Metadata Boundary
* **No Client Storage Paths:** `AssetMetadataCreate` allows clients to declare display filenames, MIME media types, positive file sizes, and SHA-256 checksums (`^[a-fA-F0-9]{64}$`). Clients are strictly forbidden from providing `storage_path`.
* **Server-Assigned Storage:** The internal `storage_path` is assigned exclusively by backend storage services upon physical file ingest.
* **Zero Binary Content in JSON:** Binary image payloads must never be embedded in JSON metadata schemas.

### Analysis Run Boundary
* **No Client-Injected Results:** `AnalysisRunCreate` accepts model names, versions, target patient/asset references, and hyperparameters. Clients **cannot** submit `status`, `results_summary`, `error_message`, or `completed_at`.
* **Segregation of Results:** Model predictions (`results_summary`) are stored separately from ground-truth clinical observations (`Observation`). AI model evaluations represent research signals and must never overwrite confirmed medical records.

### Audit Event Privacy & Integrity
* **Immutable System Records:** `AuditEventResponse` and `AuditEventFilter` provide inspection capabilities for system administrators and compliance auditors. There is **no client-facing create or update schema** for audit events; audit records are written exclusively by server-side middleware and domain services.
* **Zero PHI/Secrets in Audit Payloads:** The `event_metadata` JSON object is restricted to operational telemetry (e.g. `request_id`, execution duration). Raw clinical measurements, patient names, credentials, and authorization headers are strictly excluded.

---

## 5. Service Layer Consistency Rules & Mapping (Phase 3.6)

Pydantic schemas enforce syntactic and structural validity. Semantic business rules requiring database queries, multi-entity coordination, and transactional atomicity are implemented in the domain service layer ([`backend/app/services/`](../../backend/app/services/)):

1. **Patient-Encounter Referential Consistency:** When an `Observation`, `UploadedAsset`, or `AnalysisRun` references both a `patient_id` and an `encounter_id`, `ClinicalService` verifies that the specified encounter actually belongs to that patient, raising `ConsistencyError` on mismatch.
2. **Schema-to-Model Mapping (`mrn` ↔ `mrn_pseudonym`):** `PatientBase` accepts either `mrn_pseudonym` or `mrn` via Pydantic `AliasChoices`, mapping transparently to the underlying `Patient.mrn_pseudonym` column without altering database history.
3. **Uniqueness Collision Handling:** Uniqueness of `username`, `email`, `mrn_pseudonym`, and `storage_path` is proactively validated and translated into typed `DuplicateEntityError` domain exceptions.
4. **Transaction Ownership:** Repositories and domain services do not commit sessions automatically. Services execute operations within caller-owned transaction boundaries (e.g. `with session.begin():` or FastAPI's request-scoped `get_db_session`). If a multi-entity operation fails, the complete transaction rolls back cleanly.
5. **Audit Event Sanitization:** Operational mutations trigger audit logs via `AuditService`, where credentials (`password`, `hashed_password`, `secret_key`, `token`) are scrubbed before persistence.

---

## 6. Known Limitations & Deferred Features

* **No Public CRUD Routers (Module 4+):** Public HTTP routes utilizing these services and schemas are not yet mounted.
* **Authentication & Authorization (Module 4/7):** Hashing passwords with Argon2/bcrypt and verifying actor role permissions is deferred to future authentication modules. Repository and service access alone does not provide access control.
* **Audit Immutability Limitations:** Application-level audit records omit update/delete operations. Database-level trigger immutability and cryptographic tamper-proofing are deferred to Module 7/Module 13.
* **Physical File Upload & Verification (Module 5):** Physical file ingestion, MIME type sniffing, and byte streaming remain deferred to the storage module.
* **No Regulatory Compliance Claim:** The presence of healthcare data structures does not constitute automated HIPAA, GDPR, or CDSCO medical device compliance. Arogya AI is strictly an academic research prototype.
