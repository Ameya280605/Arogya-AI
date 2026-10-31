# Arogya AI — Pending-Review Candidate Table & Analysis Status Indicators

> **Module:** Module 5 (Overview Dashboard)<br/>
> **Phase:** 5.3 (Pending-Review Table & Analysis Status Indicators)<br/>
> **Status:** Implementation Complete & Verified<br/>
> **Component Location:** [`frontend/components/dashboard/`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/)<br/>
> **Contract Reference:** [`frontend/types/dashboard.ts`](file:///C:/_code/Projects/Arogya-AI/frontend/types/dashboard.ts) &bull; [`backend/app/schemas/dashboard.py`](file:///C:/_code/Projects/Arogya-AI/backend/app/schemas/dashboard.py)

---

## 1. Overview & Architectural Responsibilities

Phase 5.3 delivers two core presentation components for the Arogya AI Overview Dashboard (`/`):
1. **`AnalysisStatusIndicator`:** A reusable, accessible lifecycle status badge for AI analysis runs.
2. **`PendingReviewTable`:** A reusable, responsive tabular view displaying candidate analysis runs requiring clinician oversight.

Both components consume the Phase 5.1 data contracts without fabricating live clinical data or claiming that formal doctor-review workflows exist.

---

## 2. Analysis Status Indicators (`AnalysisStatusIndicator`)

The [`AnalysisStatusIndicator`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/AnalysisStatusIndicator.tsx) maps backend `AnalysisRunStatus` values to accessible clinical design tokens.

### Supported Statuses & Meanings

| Status Value | Display Label | Badge Variant | Execution Meaning |
| :--- | :--- | :--- | :--- |
| `completed` | Completed | `success` | Inference pipeline successfully concluded with research findings. |
| `running` | Running | `info` | Actively executing inference pipeline. |
| `queued` | Queued | `neutral` | Awaiting compute worker allocation. |
| `abstained` | Abstained (Safety Flag) | `warning` | Model triggered automated abstention due to high entropy, uncertainty, or safety filter threshold. |
| `failed` | Failed | `danger` | Execution terminated abnormally due to runtime error. |
| *Unknown / Future* | `Unknown ({status})` | `neutral` | Handled defensively without crashing; never falsely claims success. |

### Accessibility & Safety Tenets
- **Non-Color Reliance:** In addition to visual color styling, every status renders an explicit text label, an optional indicator dot (`withDot`), and an accessible `aria-label` (e.g. `aria-label="Analysis status: Abstained (Safety Flag)"`).
- **No Clinical Efficacy Implication:** Status denotes technical lifecycle progression only. A `completed` status indicates technical termination of the pipeline and **does not** imply diagnostic accuracy, clinical safety, or medical clearance.

---

## 3. Pending-Review Candidate Table (`PendingReviewTable`)

The [`PendingReviewTable`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/PendingReviewTable.tsx) renders a concise preview of candidate analysis runs requiring clinician triage.

### Exact Contract Fields Used (`PendingReviewItem`)

| Field Name | Type | Display Treatment in Table |
| :--- | :--- | :--- |
| `run_id` | `string` (UUID) | Shortened safe monospace identifier (`RUN-7b0a88df`) with full UUID provided in `title` and `aria-label`. |
| `patient_id` | `string` | Pseudonymous subject identifier (`SYNTH-PAT-0001`). |
| `encounter_id` | `string \| null` | Care interaction identifier (`SYNTH-ENC-0001`), or an italicized *"Unassociated"* fallback if null. |
| `model_name` | `string` | Canonical model identifier (e.g., `chexnet-v2-research`). |
| `model_version` | `string` | Semantic model version tag (e.g., `v2.1.0`). |
| `status` | `string` | Rendered via `<AnalysisStatusIndicator status={item.status} size="sm" withDot />`. |
| `abstained` | `boolean` | `<Badge variant="warning">Abstained</Badge>` when `true`, `<Badge variant="neutral">Normal</Badge>` when `false`. |
| `created_at` | `string` (ISO) | Formatted via `formatUtcTimestamp()` into standardized UTC format (e.g., `2026-01-15 11:00:00 UTC`). |

---

## 4. Review Candidates vs. Formal Doctor Review Workflow

### The Module 15 Boundary
A critical architectural boundary is maintained between candidate triage and formal clinical review:
- **Phase 5.1 & 5.3 Scope:** Candidate analysis runs are derived from unreviewed completed or abstained `AnalysisRun` records.
- **Accurate Terminology:** The table is labeled **"Analysis Runs Requiring Review"** or **"Review Candidates"**.
- **Excluded Functionality (Deferred to Module 15):**
  - Clinician assignment and re-assignment.
  - Formal sign-off and electronic signature workflows.
  - Approval, rejection, or findings override actions.
  - Persisted diagnostic amendments and clinical critique notes.
- **No Action Buttons:** The table strictly omits buttons implying that a user can approve, reject, sign off, or amend clinical results.

---

## 5. Data Provenance & Lifecycle States

The component supports four distinct lifecycle states:
1. **Populated (`ready`):** Renders table rows from verified sources. In development, data is supplied by the Module 3 seed dataset (`SYNTH-PAT-0001` cohort).
2. **Loading (`loading`):** Renders accessible skeleton placeholders in table cells with `aria-busy="true"`.
3. **Unavailable (`unavailable`):** Displays a truthful notice indicating that live backend aggregation is pending canonical Phase 5.5.
4. **Error (`error`):** Renders an alert container with `role="alert"` displaying the diagnostic error message.

### Backend API Dependency
- **Current State:** No backend dashboard aggregation endpoint exists yet (`/api/v1/health` is the only active route).
- **Roadmap Dependency:** Backend aggregation services (`DashboardService`, `DashboardRepository`) and the `GET /api/v1/dashboard/overview` endpoint are dependencies for **canonical Phase 5.5**.
- **Non-Fabrication Policy:** The overview page does not fabricate client-side mock responses or invent live clinical streams.
