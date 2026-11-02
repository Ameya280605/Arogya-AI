# Imaging Deployment Checklist and Safe Setup

This checklist covers operational setup for the research-only chest X-ray workflow. It is not a production certification, clinical validation, or a recommendation to use model output for diagnosis or treatment. Never use real patient data for deployment smoke tests.

## Before deployment

- [ ] Choose a supported Python runtime and install backend dependencies from `backend/requirements.txt`.
- [ ] Use a dedicated PostgreSQL database and a least-privilege application account. Keep `DATABASE_URL` in a secrets manager or protected environment configuration; never put credentials in command arguments, logs, source control, or support requests.
- [ ] Set `APP_ENV=staging` or `production`, `DEBUG=false`, and a unique `SECRET_KEY` of at least 32 characters through a secrets manager. Settings reject a missing, short, or built-in development key in deployment environments.
- [ ] Set `API_HOST`, `API_PORT`, and `API_PREFIX` to the intended service binding and routing prefix. Disable public API documentation if deployment policy requires it.
- [ ] Set `CORS_ALLOWED_ORIGINS` to the frontend's exact browser origin(s), including scheme and port where applicable, separated by commas. Do not use wildcard origins. Same-origin reverse-proxy deployments can leave the allowlist empty.
- [ ] Configure `UPLOAD_STORAGE_DIR` as an absolute path on durable storage outside the web root. The Grad-CAM directory is a sibling named `imaging_artifacts`; ensure both directories reside on persistent storage.
- [ ] Restrict the storage volume to the backend service identity and required administrators. On POSIX, the application enforces mode `0700` for upload/artifact directories and `0600` for files. On Windows, configure and verify restrictive NTFS ACLs; POSIX mode bits do not secure Windows volumes.
- [ ] For multiple backend replicas, use the same persistent shared storage for uploads and heatmaps. Ensure backups and restores include both directories and protect them as sensitive data.
- [ ] Provision the expected TorchXRayVision checkpoint for the *runtime service account*, or approve outbound access for first inference. The checkpoint is not in this repository. Readiness checks only that the expected cache file exists and is non-empty; it does not verify its provenance, checksum, or loadability.
- [ ] Review the current Alembic migration scripts and database privileges. Take a protected backup before migrating any database containing data.
- [ ] Confirm the patient assignment policy and operational workflow for granting access to existing patients. The migration leaves existing patients unassigned; administrators do not bypass assignments.

## Safe setup sequence (PowerShell)

Run commands from the repository root. Do not paste credentials or secret values into command lines or chat.

1. Prepare configuration without overwriting an existing local file:

   ```powershell
   if (-not (Test-Path .env)) {
       Copy-Item .env.example .env
   }
   ```

   Populate deployment values using the approved secret/configuration manager. For local-only development, protect `.env` with file-system ACLs. `.env` is ignored by Git; still check that it is not staged before any future commit.

2. Set `UPLOAD_STORAGE_DIR` to the durable absolute upload directory. Create/provision that volume and its sibling `imaging_artifacts` directory before starting the service. Apply service-account-only permissions using the host's storage/identity management; do not make either directory web-accessible.

3. Confirm which database Alembic is configured to contact before any mutation:

   ```powershell
   .\.venv\Scripts\python.exe scripts\verify_database.py --json
   .\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini current
   .\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini heads
   ```

   Verify the reported host/database and application environment against the deployment change ticket. If the target is unexpected or cannot be verified, stop. A nonzero verification result before the first migration may indicate an empty database; it is not permission to migrate without confirming the target.

4. Review the migration SQL without connecting or changing the database:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head --sql
   ```

   Review migration files and generated DDL. For a database with important data, take a backup to a private, access-controlled destination (the archive contains database contents):

   ```powershell
   .\.venv\Scripts\python.exe scripts\backup_database.py --destination "D:\protected\arogya-backups"
   ```

   Replace the example with a pre-provisioned, access-controlled destination. Confirm the backup succeeded and protect it according to the database's data-retention policy. The backup command verifies archive creation, not restore validity; test restores separately in an isolated environment.

5. Apply migrations as an explicit release step—not from application startup:

   ```powershell
   .\.venv\Scripts\python.exe -m alembic -c backend\alembic.ini upgrade head
   .\.venv\Scripts\python.exe scripts\verify_database.py --json
   ```

   Require verification status `VERIFIED`, no missing tables, and current revision equal to expected head before serving traffic. Do not run `downgrade` as a routine rollback on a database with retained data.

6. Provision and verify the model checkpoint for the same operating-system account that runs the backend. Do not commit the checkpoint or copy it from an unverified source. `GET /api/v1/ready` (or the configured `API_PREFIX`) should report database/schema and model readiness. It never downloads weights or applies migrations. The first inference may attempt a download if the cache is absent; prevent unapproved downloads by provisioning the artifact or controlling outbound network access.

7. Validate the service with synthetic fixtures or approved, de-identified public test data only. Check authentication, patient assignment, asset access, inference status, and authenticated heatmap retrieval. Do not use real patient records for smoke tests, screenshots, logs, or issue reports.

## Storage and model operations

- Preserve the database and file store as a coordinated set: database rows refer to uploaded files, and completed imaging runs refer to heatmap artifacts. A database-only restore may leave dangling asset references; a file-only restore may omit metadata and authorization context.
- Back up uploads and `imaging_artifacts` using the storage platform's protected backup mechanism. Restrict backup access, encrypt backups at rest and in transit, and test restoration without real patient records where possible.
- Keep model checkpoints outside the repository and web root. Deploy a documented model version and approved artifact provenance. Readiness is a lightweight presence check, not an ML health or integrity test.
- Use the liveness endpoint for process monitoring and readiness for traffic admission. A ready response does not prove storage durability, backup validity, CORS/browser connectivity, or clinical suitability.

## Release sign-off

- [ ] Secret/configuration values are supplied by the approved secret manager and are absent from source control and logs.
- [ ] CORS allows only the intended frontend origin(s); cookies/credentials are not enabled for wildcard origins.
- [ ] PostgreSQL target, backup, reviewed DDL, migration head, and post-migration verification are recorded in the deployment system without recording passwords.
- [ ] Uploads and heatmaps use durable, private storage with service-account-only access and tested backup/restore procedures.
- [ ] Checkpoint is provisioned for the runtime identity and its version/provenance are recorded outside PHI-bearing logs.
- [ ] Synthetic or approved de-identified smoke tests pass, including patient assignment and authenticated heatmap access.
- [ ] Users are informed that model outputs and Grad-CAM are research-only and not diagnoses or treatment guidance.
