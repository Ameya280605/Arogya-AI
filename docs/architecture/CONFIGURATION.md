# Arogya AI — Backend Configuration & Environment Validation

> **Status Notice:** Updated as of Module 3 (Database Persistence & Data Layer), Phase 3.7.<br/>
> This document specifies the validated configuration settings, environment variable bindings, type invariants, runtime hardening controls, database engine/session lifecycle mechanics, Alembic migration commands, synthetic development seed mechanisms, data access repositories & domain services, and database verification/backup/recovery procedures for Arogya AI.
>
> **Scope Boundary:**
> * **Active Configuration:** Core application identity, environment profiles, server network parameters, versioned API prefixing, logging severity, OpenAPI endpoints, synchronous PostgreSQL database engine/session infrastructure, Alembic schema migrations, synthetic development seed data, data access repositories & domain services, database verification utility, and PostgreSQL backup/restore runbooks.
> * **Placeholders & Deferred Settings:** Cryptographic secrets and application-level authentication/authorization (Module 4 / Module 7) remain validated placeholders that default to `None`. Physical database-level audit immutability triggers and multi-region disaster recovery replication remain deferred to later infrastructure phases.

---

## 1. Configuration Loading Architecture

Configuration in Arogya AI is managed using **`pydantic-settings`** ([`backend/app/settings.py`](../../backend/app/settings.py)).

### Loading & Precedence Rules
1. **Explicit Initialization:** Direct instantiation (e.g., `Settings(app_env="testing")`) takes highest precedence and is used by test fixtures to construct isolated application instances.
2. **System Environment Variables:** System-level environment variables override defaults and `.env` file entries.
3. **Dotenv File (`.env`):** Loaded from the repository root if present (UTF-8 encoded; excluded from version control).
4. **Model Defaults:** Safe fallback values for local development.

### Case-Insensitivity & Name Matching
* Environment variable names are **case-insensitive** (e.g., `APP_ENV`, `app_env`, and `App_Env` all resolve to `app_env`).
* String values for enumerated settings (such as `APP_ENV` and `LOG_LEVEL`) undergo **automatic case normalization** before schema validation.

---

## 2. Configuration Settings Reference

| Setting | Environment Variable | Type / Permitted Values | Default | Required | Description & Validation Invariants |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `app_name` | `APP_NAME` | `str` | `"Arogya AI"` | No | Human-readable application name. Must not be empty or whitespace-only. |
| `app_env` | `APP_ENV` | `'development'`, `'testing'`, `'staging'`, `'production'` | `"development"` | No | Target runtime environment profile. Normalized to lowercase. |
| `debug` | `DEBUG` | `bool` (`true`, `false`, `1`, `0`) | `False` | No | Enables FastAPI debug mode. **Strictly forbidden** when `app_env` is `'production'`. |
| `api_host` | `API_HOST` | `str` (IP or hostname) | `"127.0.0.1"` | No | Server interface binding. Defaults to loopback for secure local development. |
| `api_port` | `API_PORT` | `int` (`1`–`65535`) | `8000` | No | TCP listening port. Values outside 1–65535 raise a validation error. |
| `api_prefix` | `API_PREFIX` | `str` (starts with `'/'`) | `"/api/v1"` | No | Base routing prefix for domain endpoints. Must start with `'/'`. Trailing slashes are stripped. |
| `log_level` | `LOG_LEVEL` | `'DEBUG'`, `'INFO'`, `'WARNING'`, `'ERROR'`, `'CRITICAL'` | `"INFO"` | No | Logging severity threshold. Normalized to uppercase. |
| `openapi_url` | `OPENAPI_URL` | `str | None` | `"/openapi.json"` | No | Route path for OpenAPI 3.1 JSON schema. Set to `none`, `disabled`, or `""` to disable. |
| `docs_url` | `DOCS_URL` | `str | None` | `"/docs"` | No | Route path for Swagger UI. Set to `none`, `disabled`, or `""` to disable. |
| `redoc_url` | `REDOC_URL` | `str | None` | `"/redoc"` | No | Route path for ReDoc documentation. Set to `none`, `disabled`, or `""` to disable. |
| `database_url` | `DATABASE_URL` | `str | None` | `None` | No | PostgreSQL connection URI (e.g. `postgresql+psycopg://USER:PASSWORD@localhost:5432/arogya_ai`). Enforces PostgreSQL schemes (`postgresql`, `postgres`, `postgresql+psycopg`, `postgresql+psycopg2`, `postgresql+asyncpg`). Rejects non-PostgreSQL schemes. Empty strings and disabling tokens (`'none'`, `'null'`, `'disabled'`) normalize to `None`. Credentials masked via `masked_database_url`. |
| `secret_key` | `SECRET_KEY` | `SecretStr | None` | `None` | No | Cryptographic secret for session signing. Deferred to Module 7; empty strings normalize to `None`. |

---

## 3. Detailed Validation Invariants & Hardening Controls

### Production Debug Protection
To prevent accidental exposure of interactive debug traces or internal frames in deployed environments:
```python
@field_validator("debug")
@classmethod
def enforce_production_debug_safety(cls, debug: bool, info) -> bool:
    env = info.data.get("app_env")
    if env == "production" and debug:
        raise ValueError("debug mode cannot be enabled when app_env is 'production'")
    return debug
```
If an operator configures `APP_ENV=production` and `DEBUG=true`, the application crashes immediately during startup validation rather than running in an unsafe state.

### Interactive Documentation & Schema Endpoint Controls
In Phase 2.6, documentation endpoints (`/openapi.json`, `/docs`, `/redoc`) were added with default access. Phase 2.7 hardens the mechanism for disabling them:

1. **Environment Value Normalization:**
   * Setting `DOCS_URL=none`, `DOCS_URL=None`, `DOCS_URL=disabled`, `DOCS_URL=false`, or `DOCS_URL=""` (empty) reliably parses to Python `None`.
   * This eliminates the risk of literal strings (e.g., `"None"`) mounting Swagger UI at unexpected paths like `/None`.
2. **Valid Custom Paths:**
   * Custom paths must start with `/` (e.g., `DOCS_URL=/api-docs`). Invalid paths without leading slashes (e.g. `DOCS_URL=docs`) fail fast with a clear validation error.
3. **Cascading Schema Suppression:**
   * If `OPENAPI_URL` is disabled (`None`), [`backend/app/main.py`](../../backend/app/main.py) automatically suppresses both `docs_url` and `redoc_url` to avoid mounting broken UI shells.
4. **Security Notice:**
   * Disabling interactive documentation limits public discovery of API paths; **it is not a replacement for authentication, network authorization, or firewall restrictions**.

### Routing Prefix Sanitization
* `api_prefix` must start with a forward slash (`/`).
* Trailing slashes are stripped during settings validation (`"/api/v1/"` $\rightarrow$ `"/api/v1"`), ensuring clean, predictable path concatenation across all routers.
* Root mounting (`api_prefix="/"`) is supported for standalone single-purpose instances.

### Safe Empty Placeholders for Secrets & Database
In development templates (`.env.example`), variables such as `DATABASE_URL=` and `SECRET_KEY=` are left unpopulated:
* Empty or whitespace-only values are automatically normalized to `None` rather than empty strings or empty `SecretStr("")`.
* No placeholder credentials, default passwords, or fake API keys exist in the repository.

### PostgreSQL Connection Configuration, Engine & Session Lifecycle (Module 3)
* **Purpose of `DATABASE_URL`:** Configures the primary relational database connection for clinical entity persistence, audit logs, and metadata storage (Module 3).
* **Driver Strategy & Format:**
  * Selected modern driver strategy: **Psycopg 3** with synchronous SQLAlchemy 2.0.
  * Standard connection URI: `postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME`.
  * **Driver Scheme Normalization (`normalize_engine_url`):**
    * Legacy `postgres://` and generic `postgresql://` URIs are safely and explicitly normalized to `postgresql+psycopg://`.
    * Incompatible schemes fail fast with clear exceptions: `postgresql+asyncpg://` is rejected as incompatible with synchronous engines, and `postgresql+psycopg2://` is rejected because the project standardizes on Psycopg 3.
* **Synchronous Engine Construction (`backend/app/db/session.py`):**
  * `create_db_engine()` constructs a SQLAlchemy 2.x engine with production-ready connection pool settings:
    * `pool_pre_ping=True` (verifies connection liveness prior to checkout).
    * `pool_size=5` (baseline pool connections).
    * `max_overflow=10` (surge connections under load).
    * `pool_timeout=30.0` (seconds to wait before timeout on exhausted pool).
    * `pool_recycle=1800` (recycles connections after 30 minutes to prevent stale socket drops).
    * `connect_timeout=10` (bounded network connect timeout passed to driver).
  * Connections are acquired lazily on first query execution or pool checkout; **no network connection is established on engine instantiation**.
  * Process-wide singleton caching is managed via `get_engine()`, and test state reset is supported via `dispose_engine()`.
* **Session Lifecycle & FastAPI Dependency Injection (`get_db_session`):**
  * Sessions are created via `sessionmaker` (`autoflush=False`, `expire_on_commit=False`).
  * Yielded to FastAPI route handlers via standard dependency injection.
  * Wrapped in `try...finally`:
    * Unhandled exceptions trigger `session.rollback()`.
    * Session closure (`session.close()`) is deterministic and guaranteed across all execution paths.
    * Sessions are strictly request-scoped and never shared across concurrent requests.
* **Connection Verification (`check_database_connection`):**
  * Runs a lightweight `SELECT 1` query using an acquired connection context.
  * Translates failures to `DatabaseConnectionError` while preserving internal diagnostic causes.
  * **Zero Credential Exposure:** Error text and logs never echo submitted passwords or raw connection strings.
* **Testing Strategy (SQLite In-Memory vs. PostgreSQL Production):**
  * Offline backend unit tests use in-memory SQLite engines (`sqlite:///:memory:`) with `StaticPool` to verify session lifecycles, transaction rollbacks, and FastAPI route dependency injection without requiring live database services.
  * **Important Notice:** SQLite passes **do not establish PostgreSQL production compatibility**. SQLite lacks PostgreSQL data types (`UUID`, `JSONB`, `ARRAY`), PostgreSQL concurrency semantics, and transactional DDL behavior.
* **Application Startup Rules:**
  * Application startup (`create_app()`) strictly **must not** run `Base.metadata.create_all()` or Alembic migrations automatically. Automatic DDL on startup creates severe concurrency race conditions in clustered environments and risks unexpected schema mutations.
  * Schema migrations are managed exclusively via Alembic starting in Phase 3.5.
* **Import & Factory Safety:**
  * Importing [`backend/app/main.py`](../../backend/app/main.py), [`backend/app/db/session.py`](../../backend/app/db/session.py), or calling `create_app()` **does not initiate database connections**. Application startup remains deterministic and decoupled from database uptime during unit testing.
* **Local Connectivity Verification:**
  * When a local PostgreSQL instance is installed, daemon reachability can be checked without modifying data:
    ```powershell
    # Check PostgreSQL daemon readiness on port 5432
    pg_isready -h localhost -p 5432
    ```

---

## 4. Alembic Migrations & Schema Evolution (Phase 3.5)

Alembic provides versioned relational schema evolution decoupled from application startup:

### Migration Directory Structure
* **Configuration:** [`backend/alembic.ini`](../../backend/alembic.ini) — defines script location via `%(here)s/alembic`, file templates, and logging.
* **Environment Controller:** [`backend/alembic/env.py`](../../backend/alembic/env.py) — dynamically resolves connection targets via `Settings.database_url` or `-x db_url=...`, binds `target_metadata` to `Base.metadata`, redacts passwords from log output, and supports offline SQL generation.
* **Migration Scripts:** [`backend/alembic/versions/`](../../backend/alembic/versions/) — versioned Python migration scripts. Initial schema: [`98574e91500e_initial_schema.py`](../../backend/alembic/versions/98574e91500e_initial_schema.py).

### Standard Alembic CLI Workflows
All commands should be executed with explicit reference to `backend/alembic.ini`:

1. **Inspect Migration SQL Offline (Dry-Run / Code Review):**
   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head --sql
   ```
   *Generates pure static PostgreSQL DDL without connecting to a live database.*

2. **Inspect Current Database Revision:**
   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini current
   ```

3. **Inspect Available Head Revisions:**
   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini heads
   ```

4. **Upgrade a Dedicated Development Database:**
   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
   ```

5. **Generate a Future Migration Revision:**
   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend/alembic.ini revision --autogenerate -m "describe schema change"
   ```

### Critical Operational Rules for Migrations
* **Mandatory Review:** Autogenerated migrations must be manually inspected before application. Never apply unreviewed DDL to any shared or persistent database.
* **No Startup Migrations:** Production startup (`create_app()`) strictly **must not** run migrations or automatic DDL. Migrations must be deployed as a distinct, deliberate step in CI/CD release pipelines.
* **Downgrade Safety:** Downgrade scripts drop schema tables and destroy persistent objects. Downgrades are strictly for disposable local test environments and must never be run casually on valuable databases.
* **Pending Live Integration:** When a safe, dedicated PostgreSQL database is configured via `DATABASE_URL` in `.env`, run `alembic upgrade head` to apply schema definitions.

---

## 5. Synthetic Development Seed Data (Phase 3.5)

A standalone script ([`scripts/seed_dev_data.py`](../../scripts/seed_dev_data.py)) provides reproducible, safe development data:

### Seed Safety Controls
1. **Production & Staging Guard:** The script inspects `APP_ENV` and terminates with an error if executed in `production`, `prod`, `staging`, or `live`.
2. **Explicit Opt-in Flag:** Requires `--confirm-dev-seed` on the command line; running without this argument fails with an explicit safety error.
3. **Zero-PHI Policy:** All seeded patient records are explicitly marked `is_synthetic=True` with pseudonymous MRNs (`SYNTH-PAT-0001`). Real patient information is strictly prohibited.
4. **Zero Usable Credentials:** Seeded test users are assigned a locked account sentinel string (`!LOCKED_SYNTHETIC_DEVELOPMENT_ACCOUNT_NO_CREDENTIALS!`). No plaintext passwords or usable login credentials exist.
5. **Deterministic Idempotency:** Uses deterministic UUIDv5 identifiers generated from a fixed namespace. Repeated runs produce 0 duplicate records and modify zero existing data.
6. **Transactional Atomicity:** All records are inserted inside a single managed transaction; unhandled exceptions trigger an automatic rollback.
7. **Metadata-Only Placeholders:** Asset metadata records reference synthetic placeholder paths; no fake binary files are written to disk.
8. **Segregated AI Demoware:** Analysis runs are explicitly tagged as synthetic demonstrations with non-validated output disclaimers.

### Executing Synthetic Seed Generation
```powershell
.\.venv\Scripts\python.exe scripts/seed_dev_data.py --confirm-dev-seed
```

---

## 6. Data Access Repositories & Clinical Domain Services (Phase 3.6)

Data persistence and business logic are layered into specialized repositories and domain services:

### Package Architecture
* **Repositories (`backend/app/repositories/`):**
  * [`RoleRepository`](../../backend/app/repositories/user.py), [`UserRepository`](../../backend/app/repositories/user.py) — role queries and user account persistence.
  * [`PatientRepository`](../../backend/app/repositories/patient.py) — cohort management and pseudonymous MRN queries.
  * [`EncounterRepository`](../../backend/app/repositories/encounter.py) — clinical encounter tracking.
  * [`ObservationRepository`](../../backend/app/repositories/observation.py) — vital signs and numeric/text observation recordings.
  * [`AssetRepository`](../../backend/app/repositories/asset.py) — uploaded file metadata and SHA-256 integrity checksums.
  * [`AnalysisRepository`](../../backend/app/repositories/analysis.py) — AI model runs and evaluation output containers.
  * [`AuditRepository`](../../backend/app/repositories/audit.py) — immutable operational audit event storage.
* **Domain Services (`backend/app/services/`):**
  * [`ClinicalService`](../../backend/app/services/clinical.py) — coordinates clinical entity lifecycles, enforcing cross-entity referential integrity (patient existence, encounter ownership, observation consistency, asset consistency).
  * [`UserService`](../../backend/app/services/user.py) — coordinates user accounts and authorization roles, enforcing username and email uniqueness.
  * [`AuditService`](../../backend/app/services/audit.py) — coordinates audit logging, automatically redacting credentials (`password`, `token`, `secret_key`) from metadata.
  * [`exceptions.py`](../../backend/app/services/exceptions.py) — typed domain exceptions (`EntityNotFoundError`, `ConsistencyError`, `DuplicateEntityError`, `DomainValidationError`).

### Transaction Ownership Policy
* **Caller-Owned Transactions:** Neither repositories nor domain services commit sessions automatically. They flush changes (`session.flush()`) to enforce database constraints and populate IDs.
* **Composition & Atomicity:** Callers (e.g., FastAPI's request-scoped `get_db_session` dependency or an explicit `with session.begin():` block) control commit and rollback. If any multi-entity operation fails, the outer transaction rollback discards all uncommitted operations atomically.

### Usage Example with Session Dependency
```python
from backend.app.db.session import get_db_session
from backend.app.services.clinical import ClinicalService
from backend.app.schemas.patient import PatientCreate

# Within a FastAPI dependency or session context:
with session.begin():
    service = ClinicalService(session)
    patient = service.create_patient(
        PatientCreate(mrn_pseudonym="SYNTH-PAT-0001", is_synthetic=True)
    )
```

---

## 7. Database Verification, Backup Strategy & Disaster Recovery Runbooks

Module 3 Phase 3.7 establishes repeatable database verification, logical custom-format backup, and safe restore-testing tooling under `scripts/`.

### 7.1 Database Verification Utility (`scripts/verify_database.py`)
Performs read-only inspection of connectivity, server dialect and version, domain table completeness (via `Base.metadata.tables`), and current Alembic revision alignment without mutating, migrating, or seeding records.

**Execution Commands:**
```powershell
# Human-readable diagnostics
.\.venv\Scripts\python.exe scripts/verify_database.py

# Machine-readable JSON output (for monitoring or CI pipelines)
.\.venv\Scripts\python.exe scripts/verify_database.py --json
```

**Status & Exit Codes:**
- `0 (EXIT_SUCCESS)`: Connection verified, all 9 domain tables present, Alembic head matched.
- `1 (EXIT_CONNECTION_ERROR)`: Target database unreachable, timeout, or authentication failed.
- `2 (EXIT_SCHEMA_MISSING)`: Database reachable, but one or more domain tables are missing.
- `3 (EXIT_MIGRATION_MISMATCH)`: Tables exist, but current Alembic revision != migration head.
- `4 (EXIT_CONFIG_ERROR)`: Database URL is missing or malformed.

---

### 7.2 PostgreSQL Backup Strategy (`scripts/backup_database.py` & `.ps1`)
Creates logical PostgreSQL backups using PostgreSQL's supported `pg_dump` tool with custom archive format (`-F c`), capturing all tables, sequences, large objects, and schema metadata.

**Execution Commands:**
```powershell
# Using Python directly
.\.venv\Scripts\python.exe scripts/backup_database.py

# Using PowerShell wrapper
.\scripts\backup_database.ps1

# Custom destination directory
.\scripts\backup_database.ps1 -Destination "D:\Backups\Arogya"
```

**Operational & Security Rules:**
1. **Timestamped, Non-Overwriting Filenames:** Backups are written to `backups/arogya_ai_backup_YYYYMMDD_HHMMSS.dump`. The script strictly refuses to overwrite existing backup archives.
2. **Credential Protection:** Passwords are never passed via command-line arguments or logged. Authentication is managed via the `PGPASSWORD` subprocess environment variable or the platform PostgreSQL password file (`%APPDATA%\postgresql\pgpass.conf` on Windows; `~/.pgpass` on Linux).
3. **Integrity Validation:** Validates both the `pg_dump` return code and verifies that the output file exists and is strictly non-empty (`> 0` bytes). Empty or failed dumps are automatically cleaned up.
4. **Git Exclusion:** The `backups/` directory and `*.dump` files are ignored in `.gitignore` to prevent committing patient cohort data.
5. **Notice on Exit Code:** A successful `pg_dump` exit code proves archive creation, not logical restore validity. Periodic restore testing is required.

---

### 7.3 Safe Restore & Recovery Procedure (`scripts/restore_database.py` & `.ps1`)
Restores custom-format `.dump` archives using `pg_restore` into an **isolated, explicitly designated disposable restore-test database**.

**Execution Commands:**
```powershell
# Test restore into disposable test database 'arogya_restore_test'
.\.venv\Scripts\python.exe scripts/restore_database.py `
    --backup-file "backups/arogya_ai_backup_20261025_120000.dump" `
    --target-db "arogya_restore_test" `
    --confirm-restore-target "arogya_restore_test"

# Or using PowerShell wrapper with automated disposable cleanup
.\scripts\restore_database.ps1 `
    -BackupFile "backups/arogya_ai_backup_20261025_120000.dump" `
    -TargetDb "arogya_restore_test" `
    -ConfirmRestoreTarget "arogya_restore_test" `
    -CleanupTarget `
    -ConfirmCleanup "arogya_restore_test"
```

**Critical Safety Safeguards:**
1. **Never Restore Over Application Database:** If `--target-db` matches the configured active application database name (`settings.database_url`), the script **immediately halts and refuses execution** (exit code 6: `SAFETY_REFUSED`).
2. **Mandatory Confirmation Flag:** Requires `--confirm-restore-target <exact_target_name>` to prevent accidental typos.
3. **Protected Keyword Guard:** Refuses targets containing `prod`, `production`, `live`, or `main`.
4. **Post-Restore Schema Verification:** Connects to the restored test database and confirms all 9 domain tables exist and Alembic revision matches the expected migration head.
5. **Disposable Cleanup:** The optional `--cleanup-target` parameter drops only the explicitly confirmed restore-test database.

---

### 7.4 Backup Retention & Development Disaster Recovery Policy
* **Backup Storage Location:** `backups/` directory relative to repository root (excluded from Git).
* **Development Frequency:** Recommended daily during active schema evolution, and always immediately before running database migrations (`alembic upgrade head`) or synthetic seed generation.
* **Retention Policy:** Retain the last 7 daily development backups; manually prune archives older than 14 days. Do not automate background cron jobs in development.
* **Encryption & PHI Sensitivity:** Dumps contain pseudonymized research records. Pseudonymization does not equal anonymization. Archives must be stored on encrypted volumes (BitLocker/LUKS) with restricted filesystem permissions.
* **RPO & RTO Development Targets:**
  * **RPO (Recovery Point Objective):** 24 hours (or time of last pre-migration backup) in development.
  * **RTO (Recovery Time Objective):** < 30 minutes for a local single-node prototype rebuild.
  * *Note:* These are development targets requiring periodic manual validation, not production SLA guarantees.
* **Testing Scope Notice:** All backup/restore tests in CI/pytest use mock subprocess calls and in-memory SQLite instances to verify safety guards, credential masking, non-overwriting filenames, and table inspections. Live PostgreSQL backup and restore operations remain unverified until a dedicated PostgreSQL test container or host is configured.

---

## 8. Test Isolation & Settings Overriding

To ensure tests remain isolated and deterministic without leaking state:

1. **Singleton Caching:** `get_settings()` uses `@lru_cache(maxsize=1)`.
2. **Test Fixtures:** Automated tests inject an explicit `Settings(...)` instance via the `create_app(settings)` factory, bypassing the singleton cache.
3. **Environment Isolation:** Tests that manipulate `os.environ` must clear the cache (`get_settings.cache_clear()`) or restore original environment variables in fixture teardown.

---

## 9. Deployment Preflight Checklist

Before promoting any Arogya AI backend instance to staging or production:

- [ ] **`APP_ENV`:** Set explicitly to `staging` or `production`.
- [ ] **`DEBUG`:** Set to `false` (enforced by schema validator in production).
- [ ] **`API_HOST`:** Ensure network interface bindings match orchestrator requirements (e.g., `0.0.0.0` inside container, loopback for local dev).
- [ ] **`DOCS_URL` & `REDOC_URL`:** Evaluate whether external API documentation should be disabled (`none` or left empty).
- [ ] **Secrets:** Ensure `.env` is uncommitted and protected with strict filesystem permissions.
- [ ] **Database Preflight:** Run `scripts/verify_database.py` and confirm status `VERIFIED` (exit code 0).
- [ ] **Pre-Migration Backup:** Execute `scripts/backup_database.py` before applying new Alembic revisions.
- [ ] **Clinical Boundary Notice:** Confirm that operational test completion is not conflated with clinical decision-support certification.
