# Arogya AI

A modular, research-oriented healthcare intelligence and clinical decision-support prototype.

> **Research-Only & Clinical Safety Notice**
> Arogya AI is an academic and research prototype under development. It is not a certified medical device and does not provide autonomous clinical diagnosis or treatment. Its outputs must never replace professional medical judgment. All clinical workflows, summaries, and analytical results are intended for qualified human review, evaluation, and research exploration.

---

## 1. Project Status

- **Development Milestone:** Modules 1–10 are completed and integrated. Development is complete through Module 10; Modules 11–21 remain planned and are not yet implemented.
- **Module 9 — Tabular ML Research:** A structured-data classification baseline with reproducible training and evaluation tooling is integrated for research use.
- **Module 10 — Chest X-ray Imaging Research:** The TorchXRayVision DenseNet-121 NIH inference pipeline, authenticated imaging API, patient/image selection UI, raw score display, and optional protected Grad-CAM retrieval are integrated.
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy, Alembic migrations, Pydantic schemas, repositories, clinical services, and versioned REST endpoints.
- **Security:** Role-based access control (RBAC), explicit user-to-patient assignments with no administrator bypass, bcrypt password hashing, JWT bearer authentication, security audit events, and controlled file uploads and downloads.
- **Frontend:** Next.js 16, React, TypeScript, Vanilla CSS design tokens, responsive application shell, Overview Dashboard, Patient Intelligence workspace, Security & Asset console, and the authenticated chest X-ray research workspace.
- **Verification boundary:** Integration tests and synthetic browser verification have been run. This does not establish clinical validity or production deployment readiness.

The chest X-ray component is currently a research pipeline. Its implementation does not establish clinical validity or diagnostic reliability.

---

## 2. Project Goals & Planned Capabilities

Arogya AI is being developed incrementally. Implemented capabilities are identified separately from planned features.

### Implemented Research Modules

- **Module 9 — Tabular ML Research:** Structured-data classification baseline and reproducible evaluation tooling. Model outputs are research-only; SHAP explanations are planned, not implemented.
- **Module 10 — Chest X-ray Imaging Research:** Pretrained TorchXRayVision DenseNet-121 inference, image validation and preprocessing, held-out evaluation utilities, and optional Grad-CAM visualization. Outputs are research-only and are not clinical diagnoses.

### Planned Capabilities (Module 11 Onward)

- Multi-agent workflow orchestration, medical knowledge retrieval (RAG), and safety-aware synthesis with uncertainty and abstention.
- SHAP and evidence presentation, expanded human review and reporting, and patient timeline/follow-up workflows.
- Hospital and financial analytics, comparative model evaluation, and expanded administration and governance capabilities.
- Deployment monitoring/release workflows and the research documentation/readiness review.

**Note:** The research imaging workflow is integrated, but it is not clinically validated or ready for deployment with real patient data. See [Section 4.7](#47-backend-and-frontend-integration) and [Section 7](#7-development-setup--prerequisites) for API usage and deployment blockers.

---

## 3. Technology Direction

The following technologies support the implemented platform and planned capabilities.

- **Frontend:** Next.js 16 (App Router), React 19, TypeScript, and Vanilla CSS design tokens.
- **Backend:** Python, FastAPI, and Pydantic v2.
- **Persistence:** PostgreSQL, SQLAlchemy 2.0, and Alembic migrations.
- **Machine Learning & XAI:** scikit-learn, PyTorch, and SHAP for planned tabular explainability; TorchXRayVision and DenseNet-121 NIH pretrained weights for the integrated chest X-ray research workflow (Module 10).
- **Multi-Agent Orchestration:** LangGraph for planned workflow routing and checkpointing.
- **Local Inference (Optional):** Ollama integration where suitable local models are available.

---

## 4. Chest X-ray Imaging Research Pipeline

### 4.1 Overview

The imaging research pipeline processes a chest X-ray using a pretrained DenseNet-121 model provided by TorchXRayVision.

Its main components are:

1. **Image validation:** Checks the file format, file size, dimensions, and image readability.
2. **Image preprocessing:** Converts the image to grayscale and applies the normalization, center-cropping, and resizing steps expected by TorchXRayVision.
3. **Model inference:** Runs the pretrained model and returns its raw scores for the supported NIH-trained pathology labels.
4. **Held-out evaluation:** Provides evaluation utilities for assessing model performance on a designated evaluation split.
5. **Grad-CAM visualization:** Generates a heatmap overlay to help visualize image regions that influence a selected model score.

Grad-CAM is an interpretability technique. A highlighted region is not proof that a disease is present in that region.

### 4.2 Model Details

- **Architecture:** DenseNet-121.
- **Model weights:** `densenet121-res224-nih`.
- **Framework:** PyTorch and TorchXRayVision.
- **Inference device:** CPU.
- **Output:** Raw model scores for the model's supported pathology labels.
- **Visualization:** Grad-CAM heatmap overlay for a selected label.

The scores are **raw model scores, not calibrated probabilities**. They must not be interpreted as a patient's probability of having a disease.

### 4.3 Supported Image Inputs

The inference component supports PNG and JPEG images.

Validation includes:

- Supported file extensions: `.png`, `.jpg`, and `.jpeg`.
- Actual image contents must be PNG or JPEG.
- Maximum file size: 20 MB.
- Minimum image dimensions: 32 × 32 pixels.
- Maximum image area: 40 million pixels.
- Corrupt or unreadable images are rejected.
- Preprocessed image tensors are checked for non-finite values.

These checks help reject invalid inputs; they do not guarantee that an image is clinically suitable or that the model will produce a reliable result.

### 4.4 Running Chest X-ray Inference

Run commands from the repository root.

Use the project's configured Python environment and ensure the required imaging dependencies are installed.

```powershell
python -m ml.imaging.src.inference ".\path\to\chest_xray.png"
```

Replace the example path with the path to an available PNG or JPEG image.

The inference output includes:

- Input image filename.
- Model identifier and version information.
- Research-only status.
- Output-type information.
- Pathology labels and their corresponding raw model scores.

The checkpoint is not bundled with this repository. On first inference, TorchXRayVision downloads `nih-densenet121-d121-tw-lr001-rot45-tr15-sc15-seed0-best.pt` if it is absent from the model cache. Its default cache directory is `~/.torchxrayvision/models_data/` for the backend service account, so the first inference needs network access unless the checkpoint has been provisioned there beforehand. Model initialization is lazy: the download/load can happen on the first imaging request rather than at API startup.

### 4.5 Generating a Grad-CAM Heatmap

Grad-CAM generates a visualization for a selected pathology label.

Example:

```powershell
python -m ml.imaging.src.gradcam ".\path\to\chest_xray.png" "Pneumonia" --output ".\ml\imaging\artifacts\gradcam_pneumonia.png"
```

The command generates a heatmap overlay at the specified output path and returns metadata including:

- Input image filename.
- Selected pathology label.
- Raw model score.
- Output image path.
- Model identifier.
- Research-only status.
- A note explaining the limitations of the visualization.

The label must be supported by the model. Use an appropriate output filename and ensure the destination directory exists.

### 4.6 Testing the Imaging Components

Run the targeted Grad-CAM tests:

```powershell
python -m pytest -q .\ml\imaging\tests\test_gradcam.py
```

The current targeted test suite contains 11 passing tests covering Grad-CAM behavior, supported labels, image dimensions, JPEG inputs, and rejection of corrupt images.

Run the complete imaging test suite with:

```powershell
python -m pytest -q .\ml\imaging\tests
```

Run the full project test suite separately when performing final verification:

```powershell
python -m pytest -q
```

Test results should be recorded from the actual execution. Warnings from third-party libraries should be reviewed rather than automatically treated as failures.

### 4.7 Backend and Frontend Integration

The authenticated `/imaging` page uses already-uploaded assets; it does not upload a file as part of inference. The API prefix defaults to `/api/v1` and can be changed with `API_PREFIX`.

1. Authenticate and upload the image through `POST /api/v1/assets/upload` using multipart fields `file` and `patient_id` (and optional `encounter_id`). The upload endpoint requires `asset:upload`; patient and asset selection require the corresponding read permissions.
2. Submit `POST /api/v1/patients/{patient_id}/analysis/imaging` with a JSON body such as:

   ```json
   {
     "asset_id": "UUID-of-uploaded-asset",
     "generate_heatmap": true,
     "heatmap_label": "Pneumonia"
   }
   ```

   `encounter_id` is optional. The uploaded asset must belong to the requested patient and be PNG or JPEG. The request requires an authenticated user with `analysis:execute`.
3. Read the persisted analysis run and its `results_summary.predictions` array. The values are raw model scores, not calibrated probabilities.
4. If Grad-CAM was requested and generated, retrieve the PNG with authenticated `GET /api/v1/analysis-runs/{run_id}/imaging/heatmap` (also requires `analysis:read`). The endpoint serves only completed imaging runs with a generated heatmap.

All patient-linked API operations additionally require an explicit user-to-patient assignment; role permissions alone do not grant patient access, and administrators have no assignment bypass. Patient creators receive an initial assignment. Users with `user:manage` can grant or revoke assignments with `PUT` or `DELETE /api/v1/patients/{patient_id}/access/{user_id}`. Apply migrations through Alembic head (`20261102_access`) before deployment; existing patients are left unassigned and require explicit grants.

The frontend API client uses `NEXT_PUBLIC_API_URL`, which must include the backend origin and API prefix, for example `https://api.example.invalid/api/v1`. The frontend route is `/imaging`; unauthenticated users are shown the sign-in gate.

---

## 5. Repository Structure

The repository uses a modular monorepo structure.

```text
Arogya-AI/
├── backend/       # FastAPI application, API routers, and backend tests
├── frontend/      # Next.js web application and clinical UI
├── ml/            # Tabular ML, imaging, evaluation pipelines, and model documentation
├── data/          # Schemas, synthetic data generators, and test fixtures
├── knowledge/     # Medical reference sources and vector-index scripts
├── docs/          # Architecture decisions, governance policies, and research notes
├── tests/         # Cross-cutting integration and end-to-end tests
├── scripts/       # Developer tooling, environment verification, and database seeds
└── deployment/    # Docker configurations and deployment manifests
```

The imaging implementation is located under `ml/imaging/`, including inference, Grad-CAM, evaluation utilities, tests, and research artifacts.

Generated datasets, local evaluation splits containing identifiers, model caches, and other sensitive or machine-specific artifacts must not be committed without reviewing their contents and intended use.

---

## 6. Architecture & Governance Documentation

Detailed specifications governing system architecture, safety constraints, data policies, and execution dependencies are maintained in [`docs/`](docs/).

- **[System Architecture](docs/architecture/ARCHITECTURE.md):** Component boundaries, request flow, and trust boundaries.
- **[Configuration & Environment Validation](docs/architecture/CONFIGURATION.md):** Environment variables, validation rules, and runtime hardening.
- **[API Conventions](docs/architecture/API_CONVENTIONS.md):** REST API design, OpenAPI standards, and error handling.
- **[Security & Identity Architecture](docs/governance/SECURITY.md):** RBAC permissions, session security, file ingestion, and audit events.
- **[Intended Use & Non-Goals](docs/governance/INTENDED_USE_AND_NON_GOALS.md):** Authorized research scope, explicit non-goals, and clinical safety principles.
- **[Data Governance Framework](docs/governance/DATA_GOVERNANCE.md):** Data classification, PHI policy, dataset provenance, and incident response.
- **[Module Dependencies & Execution Order](docs/architecture/MODULE_DEPENDENCIES.md):** Module roadmap, prerequisites, and execution order.
- **[Architectural Decision Log](docs/architecture/DECISION_LOG.md):** Architecture decisions, rationales, statuses, and reconsideration triggers.

---

## 7. Development Setup & Prerequisites

Use the repository's configured Python environment and follow the setup instructions for the relevant backend, frontend, and database components.

### Quick Start & Verification

Run commands from the repository root unless otherwise indicated.

```powershell
# 1. Run the backend test suite
.\.venv\Scripts\python.exe -m pytest

# 2. Run the backend development server
.\scripts\run_backend.ps1

# 3. Verify database connectivity and schema alignment
.\.venv\Scripts\python.exe scripts/verify_database.py

# 4. Start the frontend development server
cd frontend
npm run dev

# 5. Type-check, lint, and build the frontend
npm run type-check
npm run lint
npm run build
```

### Prerequisites

- **Git:** Installed and configured.
- **Python:** Use the version supported by the repository's dependency configuration.
- **Python environment:** Install project dependencies before running services, tests, or imaging commands.
- **Node.js:** Node.js 20+ LTS is recommended for frontend development.
- **PostgreSQL:** A local PostgreSQL service or container for database-backed workflows.
- **PostgreSQL Client Tools:** `pg_dump` and `pg_restore` for logical backup and restore workflows.
- **Imaging dependencies:** PyTorch, TorchXRayVision, Pillow, NumPy, and the other dependencies specified by the project's environment configuration.

Check the repository's dependency files for the authoritative installation instructions and supported runtime versions.

### Deployment Readiness

The repository does not currently provide deployment manifests. Before exposing this research workflow, follow the [imaging deployment checklist](docs/deployment/IMAGING_DEPLOYMENT.md):

- Install the pinned backend dependency ranges from `backend/requirements.txt`; run database migrations explicitly before serving requests. Application startup does not create tables or run migrations.
- Backend settings load from the root `.env` file or process environment. Set `APP_ENV=production`, `DEBUG=false`, a reachable `API_HOST` (for example `0.0.0.0` in a container), `API_PORT`, and `API_PREFIX` as appropriate; configure `DATABASE_URL` and `SECRET_KEY`. Disable public API documentation with `OPENAPI_URL=none` if required by deployment policy.
- Configure `DATABASE_URL` for PostgreSQL and a unique, strong `SECRET_KEY` of at least 32 characters. Settings reject a missing, short, or known development secret in staging and production. Keep the key in a secret manager or protected environment variable, not source control.
- Set `UPLOAD_STORAGE_DIR` to durable storage outside the web root. On POSIX, the backend restricts upload and heatmap directories to mode `0700` and files to `0600`; on Windows, configure restrictive NTFS ACLs for the backend service account. Keep both uploads and the sibling `imaging_artifacts` directory on persistent storage; multiple API replicas need a shared volume.
- Provision the NIH checkpoint in the TorchXRayVision cache for the runtime service account or allow outbound network access for its first inference. The checkpoint is not included in the repository; a cache under a developer account does not guarantee availability to a deployed service account.
- Set `NEXT_PUBLIC_API_URL` before building the frontend; Next.js exposes this public variable in the client bundle. Configure backend `CORS_ALLOWED_ORIGINS` as a comma-separated list of exact `http://` or `https://` origins (no paths or wildcard). Development defaults to localhost origins; staging/production default to no cross-origin access. `FRONTEND_URL` alone does not configure CORS.
- `/api/v1/ready` probes database connectivity, required tables and Alembic head, and checks that the cached model checkpoint exists and is non-empty without loading model weights. It returns HTTP 503 if the database is unconfigured/unavailable, its schema is incomplete/out of date, or the checkpoint is missing/empty. It does not validate checkpoint integrity, storage durability, or perform model inference. Readiness never applies migrations.
- Patient-linked APIs require explicit user-to-patient grants; administrators do not bypass assignments. This authorization control does not constitute clinical validation, regulatory clearance, or production monitoring/release configuration. Do not use the research model for diagnosis or treatment decisions.

---

## 8. Development Workflow & Testing Expectations

Arogya AI follows a phase-by-phase development lifecycle.

1. **Bounded Phases:** Each change should belong to an approved roadmap phase with defined acceptance criteria.
2. **Evidence-Based Verification:** Tests must be executed and reported truthfully. Claims of working code should be supported by actual command outputs.
3. **Preserve Existing Functionality:** Inspect the repository before editing and avoid destructive changes to working modules.
4. **Integration Testing:** Test individual components first, then verify the interactions between backend, frontend, database, and ML services.
5. **Reproducibility:** Record relevant model versions, evaluation methods, dataset provenance, and known limitations.
6. **Safe Git Checkpoints:** Review the diff and repository status before committing changes. Exclude secrets, real patient information, and unreviewed data artifacts.
7. **Incremental Delivery:** Follow the module dependencies and avoid claiming an entire module is complete while required integration or verification remains outstanding.

---

## 9. Data Handling & Security Expectations

- **Synthetic Data and Permitted Research Data:** Development, testing, and demonstrations must use synthetic patient records or appropriately licensed, de-identified public research datasets.
- **Zero PHI Tolerance:** Real patient-identifiable information must never be imported, committed, or processed outside an explicitly authorized and appropriately governed environment.
- **Secrets Management:** Passwords, API tokens, private keys, and credentials must never be committed. Use local environment files based on `.env.example`.
- **Dataset Provenance:** Document dataset origin, access conditions, licensing, intended use, and known limitations.
- **Evaluation Integrity:** Keep evaluation data separate from training data and inspect splits for leakage risks.
- **Artifact Review:** Check generated CSV files, logs, images, and model artifacts before sharing or committing them. Local evaluation splits may contain identifiers and must be reviewed.
- **Model Limitations:** Record the model architecture, pretrained weights, evaluation methodology, and known limitations.
- **Clinical Safety:** Model scores and Grad-CAM visualizations are research outputs. They do not establish a diagnosis, confirm disease presence, or replace professional medical assessment.

---

## 10. Disclaimer

Arogya AI is an academic and research prototype. It is not a certified medical device and is not intended for independent clinical diagnosis, treatment selection, or emergency decision-making.

All model outputs, including chest X-ray scores and Grad-CAM visualizations, require appropriate interpretation and independent evaluation. No claim of clinical accuracy, safety, or readiness should be made without suitable evidence and validation.
