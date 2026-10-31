# Security, Identity & File Handling Specification (Module 7)

## 1. Overview & Trust Architecture

Module 7 establishes comprehensive server-side identity, access boundaries, cryptographic audit tracking, and safe medical asset handling for Arogya AI.

```
       [ Client Request ]
               │
               ▼
   [ Fastapi Middleware / Router ]
               │
   ┌───────────┴───────────┐
   ▼                       ▼
[ Bearer JWT ]     [ No Credentials ]
   │                       │
   ▼                       ▼
[ Decode & Validate ]  [ HTTP 401 Unauthorized ]
   │
   ▼
[ Load DB User & Roles ]
   │
   ▼
[ Evaluate Permissions ] ──(Denied)──► [ Record Security Audit Event ]
   │                                   [ HTTP 403 Forbidden ]
   ▼ (Granted)
[ Service / Storage Boundary ]
```

---

## 2. Roles & Permissions Matrix (Phase 7.1)

Access control operates on a **deny-by-default** model using canonical roles and fine-grained permissions:

| Permission | Description | Administrator | Doctor Reviewer | Researcher |
| :--- | :--- | :---: | :---: | :---: |
| `patient:read` | View patient cohort & demographics | ✅ | ✅ | ✅ |
| `patient:write` | Create & update patient records | ✅ | ✅ | ❌ |
| `encounter:read` | View clinical encounter details | ✅ | ✅ | ✅ |
| `encounter:write` | Open, complete, & cancel encounters | ✅ | ✅ | ❌ |
| `observation:read` | Inspect longitudinal vitals/labs | ✅ | ✅ | ✅ |
| `observation:write` | Record clinical observations | ✅ | ✅ | ❌ |
| `analysis:read` | Read AI analysis runs & results | ✅ | ✅ | ✅ |
| `analysis:write` | Queue new clinical analysis runs | ✅ | ✅ | ❌ |
| `asset:upload` | Ingest medical radiographs/PDFs | ✅ | ✅ | ❌ |
| `asset:read` | Download/inspect clinical assets | ✅ | ✅ | ✅ |
| `user:manage` | Manage accounts, roles, & access | ✅ | ❌ | ❌ |
| `audit:read` | Inspect immutable audit logs | ✅ | ❌ | ❌ |

---

## 3. Authentication & Protected Routes (Phase 7.2)

* **Password Hashing:** Bcrypt with cost factor 12 (`bcrypt.gensalt(rounds=12)`). Length bounded to 128 characters to prevent long-password DoS.
* **Session Handling:** PyJWT-encoded access tokens signed with `HS256` using `SECRET_KEY`.
  * Claims enforced: `sub` (user UUID), `exp` (expiration), `iat` (issued at), `jti` (unique token ID).
  * Invalidation: `/api/v1/auth/logout` endpoint records audit event and triggers client-side credential clearing.
* **Environment Secrets:** Configured via `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `UPLOAD_STORAGE_DIR`, and `MAX_UPLOAD_SIZE_BYTES`.
* **Administrator Bootstrap:** Executable CLI `scripts/bootstrap_admin.py` safely creates or updates the administrative account without hardcoding credentials in repository source files:
  ```powershell
  python scripts/bootstrap_admin.py --username admin --email admin@arogya.ai --password "<STRONG_PASSWORD>"
  ```

---

## 4. Server-Side Authorization & Isolation (Phase 7.3)

* **Enforcement:** Enforced in FastAPI route dependencies (`require_permission`, `require_role`) and verified inside domain services.
* **Cross-Patient Isolation:** Upload and query endpoints strictly validate resource ownership. Attempting to associate an asset or encounter across mismatched patient identifiers triggers a `security.cross_patient_violation` audit event and is rejected with HTTP 422.
* **Backward Compatibility:** All existing Module 5 (Overview Dashboard) and Module 6 (Patient Intelligence) routes remain fully functional with authenticated identity headers.

---

## 5. Security Audit Events (Phase 7.4)

* **Audited Operations:** Authentication successes, login failures, access denials (`auth.access_denied`), patient record modifications, cross-patient boundary violations, asset uploads, and downloads.
* **Credential Scrubbing:** `AuditService` recursively sanitizes metadata dictionaries. Any keys matching `password`, `token`, `secret`, `authorization`, `api_key`, or `bearer` are redacted to `[REDACTED_CREDENTIAL]` before database persistence.
* **Request Correlation:** Correlates with incoming HTTP `X-Request-ID` or generates a UUID for traceability.

---

## 6. Safe File Uploads & Storage Volume (Phases 7.5 & 7.6)

* **Allowed Formats & Signatures:**
  * **PNG:** Verified via magic bytes `\x89PNG\r\n\x1a\n`.
  * **JPEG:** Verified via magic bytes `\xff\xd8\xff`.
  * **PDF:** Verified via magic bytes `%PDF-`.
  * **DICOM:** Verified via 128-byte preamble followed by `DICM`.
* **Path Traversal Mitigation:**
  * Client filenames are sanitized using `Path(original_filename).name` and stripped of directory traversal sequences (`../`, `..\\`).
  * Binary files are stored under server-generated UUIDs (`<uuid>.<ext>`) in a controlled directory (`storage/uploads/`) located completely outside public web roots.
  * Attempted directory escapes are caught by `StorageService.resolve_file_path` checking `path.resolve().is_relative_to(base)`.
* **Integrity:** SHA-256 cryptographic checksum calculated and recorded in `UploadedAsset.checksum_sha256`.
* **Authorized Downloads:** Binary downloads served via authenticated `GET /api/v1/assets/{id}/download` requiring `asset:read` permission.

---

## 7. Automated Test Coverage (Phase 7.7)

Automated test suites in `backend/tests/test_security_api.py` and `backend/tests/test_assets_api.py` verify:
1. Missing, invalid, expired, and correctly signed JWT credentials.
2. Deny-by-default authorization for unauthenticated callers.
3. Role-based permission enforcement across `administrator`, `doctor_reviewer`, and `researcher`.
4. Password hashing bounds and locked account sentinels.
5. Cross-patient asset and encounter isolation.
6. Path traversal and filename injection attacks (`../../../etc/passwd.png`).
7. Disallowed extensions (`.exe`, `.sh`), spoofed MIME types, empty files, and oversized payloads.
8. Audit event generation and credential sanitization.
9. Regression verification for Modules 5 and 6 under authenticated route protection.
