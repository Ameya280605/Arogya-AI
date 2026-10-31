# Arogya AI — Summary Cards & Recent Activity Specification

> **Module:** Module 5 (Overview Dashboard)<br/>
> **Phase:** 5.2 (Summary Cards & Recent Activity)<br/>
> **Status:** Implementation Complete & Verified<br/>
> **Component Location:** [`frontend/components/dashboard/`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/)<br/>
> **Contract Reference:** [`frontend/types/dashboard.ts`](file:///C:/_code/Projects/Arogya-AI/frontend/types/dashboard.ts) &bull; [`backend/app/schemas/dashboard.py`](file:///C:/_code/Projects/Arogya-AI/backend/app/schemas/dashboard.py)

---

## 1. Overview & Architectural Boundaries

Phase 5.2 delivers reusable, accessible dashboard UI components for the Arogya AI Overview Dashboard (`/`). These components consume the strongly-typed contracts defined in Phase 5.1 without fabricating live clinical data, real-time inferencing metrics, or doctor review workflows.

### Phase Reconciliation & Roadmap Alignment
- **Discrepancy Documented:** The speculative future-phase sketch in the Phase 5.1 completion report anticipated backend aggregation services in Phase 5.2 and frontend components in Phase 5.4. However, the canonical roadmap explicitly assigns **Phase 5.2 to Summary Cards & Recent Activity UI components**.
- **Architectural Resolution:** In accordance with roadmap governance, Phase 5.2 establishes the presentation layer components, lifecycle states (`ready`, `loading`, `unavailable`, `error`), and integration into the Overview Dashboard (`/`).
- **Data Integration Boundary:** Because no backend aggregation service or HTTP endpoint exists yet (only `/api/v1/health` is currently active), the dashboard presents:
  1. A truthful **"Integration Pending"** state for unpopulated live environments.
  2. An explicitly labeled **Synthetic Demonstration** mode backed strictly by the Module 3 seed dataset (`SYNTH-PAT-0001` cohort).
  3. Real-time REST API aggregation is explicitly scheduled for Phase 5.3.

---

## 2. Implemented Components & Responsibilities

### A. Polymorphic `SummaryCard` Primitive
- **File:** [`frontend/components/dashboard/SummaryCard.tsx`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/SummaryCard.tsx)
- **Styles:** [`frontend/components/dashboard/SummaryCard.module.css`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/SummaryCard.module.css)
- **Responsibilities:**
  - Displays primary metric value with non-negative constraints (`0` is faithfully rendered as a valid count rather than an empty placeholder).
  - Displays title, contextual subtitle, unit, domain icon, and status badges.
  - Supports detailed sub-metric breakdown list (`breakdown` array).
  - Explicit provenance attribution badge (`provenance`).
  - Architectural or safety footer notes (`footerNote`).
  - Implements complete lifecycle states:
    - `loading`: Accessible skeleton placeholder with `aria-busy="true"` and `role="region"`.
    - `unavailable`: Truthful "Integration Pending" container with documented roadmap phase.
    - `error`: Alert box with `role="alert"` and descriptive status message.
    - `ready`: Populated accessible region.

### B. Specialized Domain Summary Cards
Four specialized wrappers implement domain-specific semantics from Phase 5.1 contracts:

1. **`PatientSummaryCard` (`DomainCardProps<PatientSummary>`):**
   - Renders total registered patient cohort count.
   - Shows breakdown between synthetic and licensed research subjects.
   - Enforces Zero-PHI footer notice.
2. **`EncounterSummaryCard` (`DomainCardProps<EncounterSummary>`):**
   - Renders total longitudinal care interactions.
   - Shows status breakdown (`planned`, `in_progress`, `completed`, `cancelled`).
   - Notes chronological care interaction segregation from AI inferences.
3. **`AnalysisSummaryCard` (`DomainCardProps<AnalysisSummary>`):**
   - Renders total AI pipeline execution runs.
   - Shows status distribution (`completed`, `abstained`, `running`, `queued`, `failed`).
   - Dynamically lists observed model architectures (`active_models_observed`).
4. **`ReviewQueueSummaryCard` (`DomainCardProps<PendingReviewQueueSummary>`):**
   - Strictly honest phrasing: **"Runs Requiring Review"** and **"Candidate model outputs awaiting clinician review"**.
   - Displays count of candidates awaiting review (`pending_count`).
   - Shows preview candidate count and model abstention flags (`abstained`).
   - **Review Queue Caveat:** Explains prominently that formal doctor sign-off, reviewer assignment, and critique workflows are deferred to Module 15 (Doctor Review & Feedback).

### C. `RecentActivityFeed` Component
- **File:** [`frontend/components/dashboard/RecentActivityFeed.tsx`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/RecentActivityFeed.tsx)
- **Styles:** [`frontend/components/dashboard/RecentActivityFeed.module.css`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/RecentActivityFeed.module.css)
- **Responsibilities:**
  - Consumes `RecentActivitySummary` and renders chronological event items.
  - **Safe Title Mapping:** Uses an explicit allowlist (`SAFE_EVENT_TITLES`) to map machine audit events to clinical-grade titles (e.g., `analysis.started` &rarr; "AI Analysis Execution Started", `analysis.abstained` &rarr; "Model Safety Abstention Logged").
  - **Sanitization & Zero-PHI Enforcement:** Verifies that audit descriptions omit passwords, tokens, API keys, or raw clinical narratives.
  - **Robust Timestamp Formatting:** Provides `formatUtcTimestamp()` with defensive fallbacks for missing or malformed ISO strings.
  - Supports `loading`, `empty` ("No Recent Events Recorded"), `unavailable`, and `error` states.

---

## 3. Data Sources, API Boundaries & Future Integration

| Domain | Current Persisted Source | Phase 5.2 Presentation Mode | Future Phase 5.3 Connection |
| :--- | :--- | :--- | :--- |
| **Patient Cohort** | Module 3 `Patient` table (`is_synthetic` flag) | Seed dataset (`SYNTH-PAT-0001` cohort) or Truthful Unavailable | `GET /api/v1/dashboard/overview` &rarr; `patients` |
| **Clinical Encounters** | Module 3 `Encounter` table (`status` column) | Seed dataset (`SYNTH-ENC-0001`) or Truthful Unavailable | `GET /api/v1/dashboard/overview` &rarr; `encounters` |
| **AI Analysis Runs** | Module 3 `AnalysisRun` table (`status` column) | Seed dataset (4 runs: completed, abstained) | `GET /api/v1/dashboard/overview` &rarr; `analysis` |
| **Review Candidates** | Unreviewed `completed`/`abstained` analysis runs | Candidate run preview with clear caveat | `GET /api/v1/dashboard/overview` &rarr; `reviews` |
| **Recent Activity** | Module 3 `AuditEvent` table | Seed audit events with safe title mapping | `GET /api/v1/dashboard/overview` &rarr; `recent_activity` |

### Review Queue & Activity Safety Rules
1. **Candidate Framing:** Runs marked completed or abstained are strictly labelled as candidates for review. Never claim active clinician sign-offs exist until Module 15.
2. **Untrusted Audit Descriptions:** Machine descriptions are sanitized and paired with human allowlist classifications. Raw exception stacks and credentials are never rendered.
3. **Synthetic Demo Provenance:** Whenever demonstration data is rendered, the UI displays a clear "Demonstration Provenance" badge and provenance caption referencing Module 3 seed data.
