# Arogya AI

A modular, research-oriented healthcare intelligence and clinical decision-support prototype.

> **Research-Only & Clinical Safety Notice**<br/>
> Arogya AI is an academic and research prototype under initial development. It is **not** a certified medical device, does not provide autonomous clinical diagnosis or treatment, and must never be used as a substitute for professional clinical judgment. All clinical workflows, summaries, and analytic signals generated in future phases are intended strictly for qualified clinician review, evaluation, and research exploration.

---

## 1. Project Status

* **Current Stage:** Module 7 (Security, Identity & File Handling) Complete — All Seven Phases Implemented & Verified.
* **Implementation State:** Core backend platform (FastAPI), health & error conventions, OpenAPI contracts, PostgreSQL engine/session infrastructure, 8 healthcare domain models, 46 Pydantic data schemas, Alembic migrations (`98574e91500e`), synthetic development seed data, data access repositories, clinical domain services, database verification utility, logical backup/restore tooling, database-backed `DashboardRepository`, `DashboardService`, versioned REST endpoint `GET /api/v1/dashboard/overview`, complete Patient Intelligence REST router (`/api/v1/patients`, `/api/v1/encounters`), and Module 7 Security & File Handling infrastructure (`/api/v1/auth`, `/api/v1/assets`) featuring canonical RBAC (`administrator`, `doctor_reviewer`, `researcher`), bcrypt salt-12 password hashing, PyJWT bearer token sessions, server-side route authorization dependencies, append-only security audit event logging with credential sanitization, safe MIME and magic-byte verified file ingestion (PNG, JPEG, PDF, DICOM), server-generated UUID storage outside web roots (`storage/uploads`), and resource-authorized binary downloads are implemented and verified with 231 automated backend tests across 20 test modules. Frontend foundation, design system, Overview Dashboard, Patient Intelligence workspace, and interactive Security & Asset console are complete with Next.js 16 (App Router), TypeScript, ESLint 9, Vanilla CSS design tokens, responsive application shell, 21-module canonical route architecture (`frontend/docs/ROUTES.md`), client-side token injection (`frontend/services/auth.ts`), patient cohort management, longitudinal timelines, dialog modals, data quality indicators, and interactive security controls on `/security` verified with 138 automated unit tests across 33 suites, zero TypeScript errors, zero ESLint warnings, and verified production static build across all 19 routes.



---

## 2. Project Goals & Planned Capabilities

*The following capabilities represent intended architectural directions from the project roadmap and are not yet built:*

* **Clinical Intelligence (Planned):**
  * Case intake and longitudinal context management (symptoms, vitals, lab panels).
  * Tabular risk baseline modeling with explainable feature importance (SHAP).
  * Chest X-ray imaging research pipeline with saliency visualization (Grad-CAM).
  * Agentic clinical workflow coordination (summarization, lab interpretation, imaging synthesis).
  * Medical literature retrieval-augmented generation (RAG) with strict source citation.
  * Human-in-the-loop review interface allowing clinicians to accept, modify, or reject AI-assisted findings.
* **Hospital Intelligence (Planned):**
  * Synthetic operational analytics (workload trends, department utilization).
  * Transparent infrastructure and inference resource/cost simulation models.
* **Research & Governance (Planned):**
  * Model evaluation lab comparing multi-agent architectures against single-model baselines.
  * Calibration, abstention tracking, and explicit disagreement preservation.
  * Immutable audit logging and reproducible experiment registry.

---

## 3. Technology Direction

The following technology stack has been selected for incremental adoption across planned modules:

* **Frontend:** Next.js 16 (App Router), React 19, and TypeScript with Vanilla CSS design tokens (initialized in Module 4).
* **Backend:** Python, FastAPI, and Pydantic v2 (Module 2 complete).
* **Persistence:** PostgreSQL, SQLAlchemy 2.0, and Alembic migrations (Module 3 complete).
* **Multi-Agent Orchestration:** LangGraph, evaluated for deterministic state routing and checkpointing (planned in Module 11).
* **Machine Learning & XAI:** scikit-learn, PyTorch, and SHAP, subject to platform compatibility testing (planned in Modules 9–10 & 14).
* **Local Inference (Optional):** Ollama integration where local open models are suitable (planned in Module 11/12).

---

## 4. Repository Structure

A modular monorepo structure organizes the codebase across domains:

```text
Arogya-AI/
├── backend/       # FastAPI application, API routers, and backend tests (Module 2+)
├── frontend/      # Next.js web application shell and clinical UI (Module 4+)
├── ml/            # Tabular, vision, evaluation pipelines, and model cards (Modules 9, 10, 18)
├── data/          # Schemas, synthetic data generators, and test fixtures
├── knowledge/     # Curated medical reference sources and vector index scripts (Module 12)
├── docs/          # Architecture decisions, governance policies, and research notes
├── tests/         # Cross-cutting integration and end-to-end test suites
├── scripts/       # Developer tooling, environment verification, and database seeds
└── deployment/    # Docker configurations and deployment manifests (Module 20)
```

---

## 5. Architecture & Governance Documentation

Detailed specifications governing system architecture, safety constraints, data policies, and execution dependencies are maintained in [`docs/`](docs/):

* **[System Architecture (ARCHITECTURE.md)](docs/architecture/ARCHITECTURE.md):** Target component boundaries, proposed request flow, and trust boundaries.
* **[Configuration & Environment Validation (CONFIGURATION.md)](docs/architecture/CONFIGURATION.md):** Settings reference, environment variable mappings, validation rules, and runtime hardening.
* **[API Conventions (API_CONVENTIONS.md)](docs/architecture/API_CONVENTIONS.md):** REST API design conventions, prefixing, OpenAPI documentation standards, and error envelopes.
* **[Security & Identity Architecture (SECURITY.md)](docs/governance/SECURITY.md):** RBAC permissions matrix, session security, safe file ingestion, and audit event specifications.
* **[Intended Use & Non-Goals (INTENDED_USE_AND_NON_GOALS.md)](docs/governance/INTENDED_USE_AND_NON_GOALS.md):** Authorized research scope, explicit non-goals, and clinical safety tenets.
* **[Data Governance Framework (DATA_GOVERNANCE.md)](docs/governance/DATA_GOVERNANCE.md):** Data classification, zero-PHI policy, dataset provenance, and incident response.
* **[Module Dependencies & Execution Order (MODULE_DEPENDENCIES.md)](docs/architecture/MODULE_DEPENDENCIES.md):** Full 21-module roadmap matrix, prerequisites, and parallelization rules.
* **[Architectural Decision Log (DECISION_LOG.md)](docs/architecture/DECISION_LOG.md):** Provisional ADRs, rationales, statuses, and reconsideration triggers.

---

## 6. Development Setup & Prerequisites

The backend application runtime is configured with Python 3.14+ in the isolated `.venv` environment.

### Quick Start & Verification
```powershell
# 1. Run backend test suite (231 tests)
.\.venv\Scripts\python.exe -m pytest

# 2. Run backend development server
.\scripts\run_backend.ps1

# 3. Verify database connectivity & schema alignment
.\.venv\Scripts\python.exe scripts/verify_database.py

# 4. Frontend: Run development server
cd frontend
npm run dev

# 5. Frontend: Type-check, lint, and production build
npm run type-check
npm run lint
npm run build
```

### Verified Prerequisites
* **Git:** Version control installed.
* **Python:** 3.11+ (Python 3.14.6 verified in project virtual environment).
* **Node.js:** Node 20+ LTS recommended (host has Node 24.18.0 installed).
* **PostgreSQL:** Local PostgreSQL service or container (for live database workflows).
* **PostgreSQL Client Tools:** `pg_dump` and `pg_restore` (for logical backup and restore workflows).

---

## 7. Development Workflow & Testing Expectations

Arogya AI adheres to a strict phase-by-phase development lifecycle:
1. **Bounded Phases:** Every change must belong to a single approved roadmap phase with defined acceptance criteria.
2. **Evidence-Based Verification:** Tests must be executed and reported truthfully; claims of working code must be accompanied by actual command outputs.
3. **No Premature Implementation:** Modules must strictly follow prerequisite dependencies (Foundation $\rightarrow$ Core Workflows $\rightarrow$ AI Research $\rightarrow$ Human Review $\rightarrow$ Platform Completion).

---

## 8. Data Handling & Security Expectations

* **Synthetic Data Only:** All development, testing, and demonstrations must use synthetic patient data or appropriately licensed, de-identified public research datasets.
* **Zero PHI Tolerance:** Real patient identifiable information (PHI/PII) must **never** be imported, committed, or processed.
* **Secrets Management:** Passwords, API tokens, and private keys must never be committed. Use local `.env` files based on [`.env.example`](.env.example).
"# Arogya-AI-Agent" 
