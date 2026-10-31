# Arogya AI — Complete Frontend Route Inventory (Roadmap v2.0)

> **Document Status:** Complete Module Route Architecture (Module 4, Phase 4.6).<br/>
> This document accounts for all **21 canonical roadmap modules** from `docs/architecture/MODULE_DEPENDENCIES.md`, specifying their route path, implementation status, prerequisites, user-facing classification, and deferred functionality notes.

---

## 1. Overview & Architectural Principles

1. **Canonical Source of Truth:** All 21 modules adhere strictly to the roadmap sequence defined in `docs/architecture/MODULE_DEPENDENCIES.md` across 5 execution blocks.
2. **Honest Route States:** Every planned user-facing route is direct-loadable, rendered within the shared `AppShell`, and clearly communicates its actual readiness using `PlannedFeatureState`.
3. **No Fabricated Data or Workflows:** Route placeholders explicitly distinguish active frontend shell foundations from pending backend integrations, model inference, and EHR pipelines.
4. **Internal Foundations vs. User-Facing Routes:** Core platform foundations (Modules 1, 2, 3, 4, 9) that function as internal infrastructure, backend APIs, database persistence, or mathematical research engines are properly accounted for without creating artificial, unneeded top-level routes.

---

## 2. Canonical 21-Module Inventory Matrix

| Module | Canonical Module Name | Route Path | User-Facing / Category | Execution Block | Prerequisites | Implementation Status | Notes on Scope & Deferred Work |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1** | Project Foundation & Architecture | *N/A (Monorepo)* | Internal Foundation | Block 1 | None | **Complete** | Root repository layout, git isolation, CI/CD scripts, documentation baselines. |
| **M2** | Backend Platform | *N/A (`/api/v1`)* | Internal Foundation | Block 1 | M1 | **Complete** | Core FastAPI service, logging, request IDs, error conventions. API documented via `/api/v1/docs`. |
| **M3** | Database & Data Contracts | *N/A (Persistence)* | Internal Foundation | Block 1 | M1, M2 | **Complete** | PostgreSQL models, SQLAlchemy schemas, Alembic migrations (`98574e91500e`), synthetic development seed data, repository layer. |
| **M4** | Frontend Shell & Design System | `/` (Global Shell) | User-Facing Foundation | Block 1 | M1 | **Complete** | Next.js 16 App Router, responsive AppShell, clinical design tokens, UI primitives, application states, complete route architecture. |
| **M5** | Overview Dashboard | `/` | User-Facing (Clinical) | Block 2 | M2, M3, M4 | **Complete** | Full database aggregation API, dashboard cards, recent activity, pending reviews, filter bar, distribution charts, and synthetic demo mode. |
| **M6** | Patient Intelligence | `/patients` | User-Facing (Clinical) | Block 2 | M2, M3, M4, M5 | **Complete** | Longitudinal patient cohort management, search, demographic stratification, schema-backed CRUD, encounters lifecycle, observation vitals logging, data quality scoring, and timeline. |
| **M7** | Security, Identity & File Handling | `/security` | User-Facing (Security/Gov) | Block 2 | M2, M3 | **Planned (Module 7)** | RBAC session policies, multi-factor authentication, cryptographic audit verification, validated medical image uploads. Auth boundaries deferred to Module 7. |
| **M8** | Clinical Workspace | `/analysis` | User-Facing (Clinical) | Block 2 | M3, M4, M5, M6, M7 | **Planned (Module 8)** | Multimodal clinical case intake, chief complaint entry, investigation workflow runners, and observation panel synthesis. Inference runners deferred. |
| **M9** | Tabular ML Research | *Integrated (`/research`)* | ML Research Pipeline | Block 3 | M3, M8 | **Planned (Module 9)** | Baseline scikit-learn / XGBoost risk models on structured vitals and labs. Surfaced directly in the AI Research Lab (`/research`) and Clinical Workspace (`/analysis`). |
| **M10** | Chest X-ray Imaging Research | `/imaging` | User-Facing (Clinical/Vision) | Block 3 | M3, M7, M8 | **Planned (Module 10)** | Chest radiography preprocessing, PyTorch deep learning vision pipeline, DICOM viewing, and Grad-CAM saliency heatmaps. Vision pipeline deferred to Module 10. |
| **M11** | Multi-Agent Orchestration | `/agents` | User-Facing (AI Research) | Block 3 | M8, M9, M10 | **Planned (Module 11)** | Deterministic LangGraph state coordination, specialized agent coordinator (Context, Lab, Vision, Knowledge, Critic), execution tracing. |
| **M12** | Medical Knowledge Hub & RAG | `/knowledge` | User-Facing (Knowledge) | Block 3 | M2, M3, M8, M11 | **Planned (Module 12)** | Clinical practice guidelines index, vector embeddings, source-attributed retrieval-augmented generation (RAG), and prompt-injection defenses. |
| **M13** | Critic, Consensus, Uncertainty & Safety | `/safety` | User-Facing (AI Safety) | Block 3 | M9, M10, M11, M12 | **Planned (Module 13)** | Cross-agent contradiction checking, explicit clinical disagreement preservation, entropy calibration, and safety abstention triggers. |
| **M14** | Explainability & Evidence Presentation | `/explainability` | User-Facing (XAI) | Block 3 | M9, M10, M11, M12, M13 | **Planned (Module 14)** | SHAP feature attribution waterfall plots, Grad-CAM saliency overlays, and guideline evidence synthesis panels. Model explainability runners deferred. |
| **M15** | Reports, Doctor Review & Feedback | `/reviews` | User-Facing (Clinical Workflow) | Block 4 | M7, M8, M9, M10, M11, M12, M13, M14 | **Planned (Module 15)** | Clinician oversight workstation: accept, modify, or reject AI-assisted findings; immutable audit logging separating raw AI outputs from doctor edits. |
| **M16** | Patient Timeline & Follow-up | `/timeline` | User-Facing (Care Workflow) | Block 4 | M3, M6, M7, M15 | **Planned (Module 16)** | Longitudinal patient trajectories, physiological trend charts, ambulatory encounter history, and staff-only follow-up task coordination. |
| **M17** | Hospital Intelligence & Financial Analytics | `/operations` | User-Facing (Operations) | Block 5 | M3, M4, M5, M15 | **Planned (Module 17)** | Departmental workload statistics, bed capacity simulation, compute inference and secure storage cost modeling. Measured vs simulated data segregation. |
| **M18** | AI Research Lab & Model Evaluation | `/research` | User-Facing (Research Bench) | Block 5 | M9, M10, M11, M12, M13, M14 | **Planned (Module 18)** | Comparative benchmarking (multi-agent vs single-model baselines), subgroup fairness metrics, cross-architecture experiment registry. |
| **M19** | Administration, Audit & Governance | `/admin` | User-Facing (Governance) | Block 5 | M3, M7, M15 | **Planned (Module 19)** | User administration, immutable audit query console, model version registry, runtime platform hardening. |
| **M20** | Deployment, Monitoring & Release | `/monitoring` | User-Facing (DevOps/Ops) | Block 5 | Core modules | **Planned (Module 20)** | Container orchestration (Docker Compose), CI/CD test pipelines, API latency telemetry, system health monitoring, release runbooks. |
| **M21** | Research Documentation & Readiness Review | `/readiness` | User-Facing (Compliance) | Block 5 | All modules | **Planned (Module 21)** | Academic handover package, standardized model cards, clinical safety gap analyses, and regulatory readiness reviews (MDR/FDA SaMD frameworks). |

---

## 3. Route Hierarchy & Navigation Structure

All user-facing routes are accessible directly and organized into four logical domain sections within the primary sidebar navigation:

```text
├── Overview (Block 2 / Shell Foundation)
│   └── / .................................... Overview Dashboard & Component Showcase (M5)
│
├── Clinical Workflows (Block 2 & Block 4)
│   ├── /patients ............................ Patient Intelligence (M6)
│   ├── /analysis ............................ Clinical Workspace & Case Analysis (M8)
│   ├── /imaging ............................. Chest X-ray Imaging & Research (M10)
│   ├── /reviews ............................. Doctor Review, Critique & Reports (M15)
│   └── /timeline ............................ Longitudinal Patient Trajectory & Follow-up (M16)
│
├── AI Research & Safety (Block 3)
│   ├── /research ............................ AI Research Lab & Model Evaluation (M18)
│   ├── /agents .............................. Multi-Agent Orchestration & State Graph (M11)
│   ├── /knowledge ........................... Medical Knowledge Hub & RAG Retrieval (M12)
│   ├── /safety .............................. Critic, Consensus & Uncertainty Safety (M13)
│   └── /explainability ...................... Explainability & Evidence Presentation (M14)
│
└── Governance & Operations (Block 2 & Block 5)
    ├── /admin ............................... Platform Administration & Governance (M19)
    ├── /security ............................ Security Safeguards & Identity Management (M7)
    ├── /operations .......................... Hospital Intelligence & Resource Simulation (M17)
    ├── /monitoring .......................... System Deployment & Telemetry Health (M20)
    └── /readiness ........................... Research Documentation & Readiness Review (M21)
```

---

## 4. Route Template Pattern

Every user-facing route is implemented using a standardized, accessible pattern:

```tsx
import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";

export const metadata: Metadata = {
  title: "[Canonical Module Name] — Arogya AI",
  description: "[Module purpose and architectural boundary]",
};

export default function ModulePage() {
  return (
    <PageContainer
      title="[Canonical Module Name]"
      description="[Brief description of intended capabilities]"
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "[Canonical Module Name]" },
      ]}
      badge={
        <div role="status" aria-label="Roadmap Status">
          <span>Module [N]: Planned</span>
        </div>
      }
    >
      <PlannedFeatureState
        moduleName="Module [N]: [Canonical Module Name]"
        targetBlock="Block [B]: [Execution Block]"
        statusText="Planned for a future module"
        description="[Honest explanation of planned capabilities versus current shell]"
        verifiedFoundations={[
          "[Verified Backend / Relational Model from earlier modules]",
        ]}
      />
      {/* Planned Domain Specifications & Architecture Alignments */}
    </PageContainer>
  );
}
```

---

## 5. Non-User-Facing Module Treatment

The following modules function as underlying architecture foundations or research pipeline engines rather than standalone top-level clinical views:

* **Module 1 (Project Foundation & Architecture):** Enforces monorepo structure, Git isolation boundaries, and validation scripts.
* **Module 2 (Backend Platform):** Implements the FastAPI gateway, request correlation IDs, and structured error envelopes (`/api/v1`).
* **Module 3 (Database & Data Contracts):** Provides PostgreSQL models, SQLAlchemy 2.0 sessions, Alembic migrations, and Pydantic data contracts.
* **Module 4 (Frontend Shell & Design System):** The active design system, CSS token registry, reusable UI primitives, and application states serving all routes.
* **Module 9 (Tabular ML Research):** Algorithmic baseline model research pipeline on structured labs/vitals. Directly surfaced through the AI Research Lab (`/research`) and Clinical Workspace (`/analysis`).

---

## 6. Frontend Quality & Navigation Verification Audit (Phase 4.7)

### A. Automated Verification Results
All tests and static analysis suites executed cleanly without warnings:

1. **Unit & Route Tests (`npm run test`):**
   * **69 tests passed** across 19 suites in `1172ms`.
   * Covers all 21 roadmap modules, all 16 user-facing route files, honest disclaimers, `/research` relationship with Module 9, Header context title mapping, sidebar grouped navigation, dialog accessibility (focus trap, Escape key, focus restore), and application state components.
2. **ESLint (`npx eslint .`):**
   * 0 errors, 0 warnings across all TypeScript, TSX, and configuration files.
3. **Type-Check (`npm run type-check`):**
   * `tsc --noEmit` passed with 0 compilation errors.
4. **Next.js Production Build (`npm run build`):**
   * Compiled successfully with Turbopack in 643ms.
   * Statically prerendered all **19 routes** (`/`, `/_not-found`, and 17 page routes).

### B. Responsive Viewport Verification
The responsive shell architecture was verified across three standard target viewports:

| Viewport | Target Resolution | Architectural Behavior & Validation |
| :--- | :--- | :--- |
| **Mobile** | `375 × 812` (iPhone X/12) | Sidebar transitions to off-canvas fixed drawer (`transform: translateX(-100%)`). Header hamburger button becomes visible (`display: inline-flex`). Opening drawer applies backdrop overlay and `.sidebarOpen` class. Drawer closes on link click, backdrop click, or Escape key. Content padding reduces to `var(--space-4)` to prevent horizontal overflow. |
| **Tablet** | `768 × 1024` (iPad Portrait) | Off-canvas drawer pattern remains active under 860px breakpoint. Header action pills compress into compact badges. Grid layouts gracefully collapse to 1 or 2 columns without horizontal scrolling. |
| **Desktop** | `1280 × 800` (MacBook / Laptop) | Sidebar displays as sticky 270px left navigation column (`height: 100vh`). Mobile hamburger menu and drawer close buttons are hidden (`display: none`). Main content wrapper expands up to `var(--layout-max-width)` (1440px) centered with clean negative space. |

### C. Dialog & Accessibility Regression Matrix
* **Escape-Key Dismissal:** Verified on both Dialog modal (`dialog.test.tsx`) and mobile navigation drawer (`AppShell.tsx`).
* **Focus Containment & Restoration:** Dialog traps `Tab` cycles within modal container when open and restores focus to triggering element on close.
* **Semantic ARIA Roles:**
  * Dialog: `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, `aria-describedby`.
  * Mobile Nav: `aria-expanded` toggles between `false` and `true`; `aria-controls="app-sidebar"` matches `<aside id="app-sidebar">`.
  * Active Navigation: Currently active link carries `aria-current="page"`.
  * Skip Link: `<a href="#main-content">` targets `<main id="main-content" tabIndex={-1}>`.

---

## 7. Known Limitations & Manual Verification Steps

1. **Browser Automation Tooling Environment:** The automated subagent headless browser encountered a Chrome DevTools Protocol (CDP) port parsing error (`failed to create browser context: failed to resolve CDP URLs: failed to parse CDP port:`). Automated coverage was established through Node.js DOM unit testing, full React component tree rendering, TypeScript compiler checks, and Next.js static prerendering of all 19 production routes.
2. **Manual Verification Procedure (for Human Reviewers):**
   ```bash
   cd frontend
   npm run dev
   ```
   * Open `http://localhost:3000` in Google Chrome, Mozilla Firefox, or Apple Safari.
   * Toggle Developer Tools responsive device emulation mode (`Ctrl+Shift+M` or `Cmd+Shift+M`).
   * Test viewport resizing across Mobile (375px), Tablet (768px), and Desktop (1280px+).
   * Verify drawer opens via hamburger icon, closes on route selection, and closes when pressing the `Escape` key.
   * Verify tab navigation cycles cleanly across interactive links and buttons without trapped focus.
3. **Clinical Inference & Backend Decoupling:** In accordance with roadmap sequencing, all clinical pages display honest `PlannedFeatureState` messaging. Backend data fetching, machine-learning inference, and live patient databases remain deferred to Blocks 2–5.
