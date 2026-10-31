# Arogya AI — Architectural Decision Log (ADR)

> **Document Purpose:** This register records key architectural decisions, foundational technology selections, design rationales, and reconsideration triggers for Arogya AI.<br/>
> As a research prototype, decisions marked `Proposed` or `Needs validation` remain open to empirical revision during subsequent module implementations.

---

## Decision Status Legend
* **Accepted:** Approved architectural baseline for initial foundation development.
* **Proposed:** Recommended architectural direction pending module-level implementation review.
* **Needs validation:** Subject to empirical benchmarking, hardware compatibility, or performance testing.
* **Superseded:** Replaced by a subsequent decision record.

---

## Architectural Decision Register

| ID | Decision Topic | Status | Rationale Summary | Reconsideration Trigger |
| :--- | :--- | :--- | :--- | :--- |
| **ADR-001** | **Modular Monorepo Architecture** | **Accepted** | Keeps frontend, backend, ML pipelines, and schemas synchronized in a single repository; avoids distributed deployment overhead during rapid prototyping. | Substantial repository size growth (>5GB) due to multi-domain assets or severe CI build slowdowns. |
| **ADR-002** | **FastAPI & Pydantic v2 for Backend API** | **Accepted** | Provides native async support, automatic OpenAPI contract generation, strict type validation, and high performance for Python data services. | Inability to handle high-throughput async streaming or integration conflicts with downstream ML pipelines. |
| **ADR-003** | **Next.js & TypeScript for Frontend** | **Accepted** | Modern component ecosystem, strong static typing, server-side rendering for data visualization, and accessibility support. | Unnecessary framework complexity if client requirements shift to a pure lightweight SPA. |
| **ADR-004** | **PostgreSQL with SQLAlchemy 2.0 & Alembic** | **Accepted** | Robust ACID transactional semantics, declarative schema modeling, and controlled migration tracking for clinical and audit entities. | Extreme multi-modal unstructured storage bottlenecks requiring document-store native features. |
| **ADR-005** | **Decoupled Research ML Services** | **Accepted** | Isolates heavy computer vision and tabular ML dependencies from core API execution; prevents packaging bloat in standard web services. | Communication latency overhead between orchestrator and models becomes prohibitive in local testing. |
| **ADR-006** | **LangGraph as Candidate AI Orchestrator** | **Needs validation** | Provides cyclic and deterministic state-graph coordination, checkpointing, and inspectable transitions across multi-agent workflows. | Excessive runtime overhead, brittle state management, or if linear pipeline execution suffices. |
| **ADR-007** | **Synthetic & Licensed Public Data Only** | **Accepted** | Guarantees zero patient privacy risk during development; enables open academic collaboration without institutional PHI exposure. | Transition to authorized institutional clinical trial protocol with formal ethics review. |
| **ADR-008** | **Mandatory Human-in-the-Loop & Uncertainty Reporting** | **Accepted** | Clinical safety mandate: AI generated outputs must never act autonomously; clinicians retain review authority and system must abstain on low confidence. | Regulatory clearance of specific autonomous SaMD algorithms (outside current academic scope). |
| **ADR-009** | **Python 3.14 Host vs. ML Ecosystem Pinning** | **Needs validation** | The current host environment has Python 3.14.6 installed. Heavy data science and ML packages (e.g., PyTorch, SHAP) may lack pre-built Windows wheels. | Installation failure of scientific dependencies during Module 2 or Module 9; will trigger containerization or Python 3.11/3.12 pinning. |

---

## Detailed Decision Records

### ADR-001: Modular Monorepo Architecture
* **Context:** Arogya AI requires cross-cutting consistency between data schemas, backend endpoints, frontend views, and research documentation.
* **Decision:** House all components (`backend/`, `frontend/`, `ml/`, `data/`, `knowledge/`, `docs/`, `tests/`, `scripts/`, `deployment/`) within a unified repository.
* **Consequences:** Simplifies refactoring and version tracking. Requires disciplined `.gitignore` rules to prevent check-in of heavy ML weights or binary data.

### ADR-006: LangGraph Multi-Agent Orchestration
* **Context:** Module 11 requires coordinating clinical context extraction, lab rule interpretation, imaging analysis, and medical literature retrieval.
* **Decision:** Evaluate LangGraph as the stateful coordination engine.
* **Validation Criteria:** Must support deterministic timeouts, per-agent partial failure isolation, and transparent inspection without exposing raw internal reasoning tokens.

### ADR-009: Python Environment & Version Compatibility
* **Context:** The host developer machine runs Python 3.14.6. Pre-compiled binary wheels for PyTorch and SHAP are historically delayed for early Python minor releases on Windows.
* **Decision:** Assess package resolution during Module 2 setup. If wheels fail, use Docker containerization or Python 3.11/3.12 virtual environment without altering the project structure.
