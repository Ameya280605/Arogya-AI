# Arogya AI — Dashboard Filters & Visualizations

> **Module:** Module 5 (Overview Dashboard)<br/>
> **Phase:** 5.4 (Dashboard Filters & Visualizations)<br/>
> **Status:** Implementation Complete &amp; Verified<br/>
> **Component Location:** [`frontend/components/dashboard/`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/)<br/>
> **Documentation Location:** [`docs/dashboard/`](file:///C:/_code/Projects/Arogya-AI/docs/dashboard/)

---

## 1. Objective & Scope

Phase 5.4 implements accessible, interactive date-range and analysis-status filtering controls alongside lightweight, semantic distribution charts for the Arogya AI Overview Dashboard (`/`).

Key principles guiding this implementation:
1. **Lightweight &amp; Self-Contained:** Zero external charting dependencies (avoiding heavyweight client bundles and hydration mismatches). Built entirely using semantic HTML5, Vanilla CSS tokens, and accessible SVG/Table primitives.
2. **Dynamic Responsiveness:** Filters dynamically propagate to analysis summaries, review queues, activity feeds, and visual distribution metrics.
3. **Rigorous UTC Handling:** Date range boundaries strictly parse and validate UTC millisecond limits without timezone drift.
4. **Clinical Research Safety Boundary:** Diagnostic performance benchmarks (ROC curves, sensitivity/specificity, calibration) are intentionally omitted from the Overview Dashboard.

---

## 2. Filter Controls &amp; Behaviors (`DashboardFilterBar`)

The [`DashboardFilterBar`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/DashboardFilterBar.tsx) provides a centralized, keyboard-operable control bar located above the summary metrics.

### Filter Fields &amp; Validation

| Control | Input Type | Scope / Validation | Default |
| :--- | :--- | :--- | :--- |
| **Start Date** | HTML5 `date` | UTC boundary `[startDate]T00:00:00.000Z`. Validated against `endDate`. | Empty (`""`) |
| **End Date** | HTML5 `date` | UTC boundary `[endDate]T23:59:59.999Z`. Validated against `startDate`. | Empty (`""`) |
| **Analysis Status** | Accessible `<Select>` | Canonical statuses: `all`, `completed`, `running`, `abstained`, `queued`, `failed`. | `"all"` |
| **Reset Filters** | Accessible `<Button>` | Resets all filters back to default. Automatically disabled when all filters are default or component is disabled. | Disabled when clean |

### Validation &amp; Error Handling
- **Reversed Range Detection:** When `startDate > endDate`, an accessible notice is rendered with `role="alert"`:
  *"Invalid date range: Start date ({startDate}) must precede or equal end date ({endDate})."*
- Both inputs receive `invalid={true}` and `aria-invalid="true"`.
- When an invalid date range is present, filtering logic yields an empty dataset safely without throwing runtime exceptions.
- **Active Filter Counter:** A badge indicates active filter counts (e.g., `"1 Active"`, `"2 Active"`, or `"All Records"`).

---

## 3. Filter Target Matrix: Which Sections Respond

| Dashboard Section | Component | Responding Criteria | Non-Responding Aspects &amp; Justification |
| :--- | :--- | :--- | :--- |
| **Patient Summary Card** | `PatientSummaryCard` | Static synthetic cohort scope | Patient registry reflects static cohort size (10 subjects in Module 3 seed data). Not dynamically filtered by run status. |
| **Encounter Summary Card** | `EncounterSummaryCard` | Static care event period | Encounter periods define fixed historical observation windows (`2026-01-01` to `2026-01-31`). |
| **Analysis Summary Card** | `AnalysisSummaryCard` | Status filter &amp; Date range | Filtered dynamically: When status is selected, total runs isolates that status; when date falls outside observation period, runs drop to 0. |
| **Review Queue Summary Card** | `ReviewQueueSummaryCard` | Status filter &amp; Date range | Filtered dynamically: Candidate count reflects runs matching selected status and date range. |
| **Visualizations: Status Distribution** | `DashboardVisualizations` | Status filter &amp; Date range | Reflects dynamically filtered execution states; highlights or isolates selected status. |
| **Visualizations: Model Distribution** | `DashboardVisualizations` | Status filter &amp; Date range | Derives model distribution dynamically from filtered candidate review items. |
| **Pending Review Table** | `PendingReviewTable` | Status filter &amp; Date range | Filters candidate rows matching status (`item.status`) and UTC timestamp (`item.created_at`). |
| **Recent Activity Feed** | `RecentActivityFeed` | Status filter &amp; Date range | Filters operational audit log by matching `analysis.{status}` and event UTC timestamps. |

---

## 4. Visualizations Architecture (`DashboardVisualizations`)

The [`DashboardVisualizations`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/DashboardVisualizations.tsx) component implements two core distribution charts:

### Chart 1: Analysis Run Lifecycle Distribution
- **Objective:** Displays relative proportion of execution states across AI pipelines.
- **Data Source:** `AnalysisSummary.by_status` (`completed`, `abstained`, `running`, `queued`, `failed`).
- **Visual Presentation:** Proportionate horizontal bars styled with canonical design tokens (`var(--color-success-primary)`, `var(--color-warning-primary)`, `var(--color-info-primary)`, `var(--color-danger-primary)`).
- **Accessibility Alternative:** A fully structured accessible `<Table>` with `<TableCaption>`, column headers (`scope="col"`), and precise percentage shares for assistive technologies.

### Chart 2: Review Candidates by Research Model
- **Objective:** Displays candidate analysis runs awaiting clinical oversight grouped by model architecture.
- **Data Source:** Dynamically derived from `PendingReviewQueueSummary.items` grouped by `item.model_name` and semantic versions (`item.model_version`).
- **Visual Presentation:** Proportional horizontal bar tracks with model names in monospace styling and candidate count labels.
- **Accessibility Alternative:** Accessible `<Table>` summarizing model architecture, version tags, candidate count, and cohort share.

---

## 5. Intentionally Omitted Visualizations &amp; Safety Boundary

Per the research governance framework and prompt specifications:

1. **Diagnostic Performance Benchmarks Omitted:**
   - ROC (Receiver Operating Characteristic) curves, AUC metrics, sensitivity/specificity curves, and calibration plots are **intentionally excluded** from the Overview Dashboard.
   - **Rationale:** Algorithmic performance metrics require formal multi-model validation sets, cross-validation splits, and statistical significance testing. These capabilities are architecturally assigned to **Module 18 (AI Research Lab)** and **Module 9 (Tabular ML Research)**.
2. **Clinical Decision Disclaimer:**
   - Visualizations depict **operational pipeline execution states** and **candidate review counts**, never clinical efficacy, disease prevalence, or diagnostic confidence.
   - A dedicated research safety boundary notice is permanently embedded beneath the charts.

---

## 6. Data Provenance &amp; Lifecycle Presentation States

The visualization and filtering layer supports four presentation states:
- **`ready` (Synthetic Demonstration):** Consumes the seeded `SYNTH-PAT-0001` cohort (Module 3). Clearly labeled as demonstration data.
- **`loading`:** Accessible skeleton placeholders with `aria-busy="true"`.
- **`unavailable`:** Explanatory banner confirming that backend aggregation endpoints are scheduled for Phase 5.5.
- **`error`:** Semantic alert banner (`role="alert"`) displaying synchronization errors without crashing the dashboard.

---

## 7. Roadmap Continuity: Remaining Module 5 Work

| Phase | Title | Scope &amp; Target Deliverables |
| :--- | :--- | :--- |
| **Phase 5.1** | Overview Data Contracts | Typed schemas in backend &amp; frontend contracts (**Complete**). |
| **Phase 5.2** | Summary Cards &amp; Recent Activity | Reusable metric cards and sanitized audit feed (**Complete**). |
| **Phase 5.3** | Pending-Review Table &amp; Status Indicators | Review table and lifecycle indicators (**Complete**). |
| **Phase 5.4** | Dashboard Filters &amp; Visualizations | UTC date/status filters and distribution charts (**Complete**). |
| **Phase 5.5** | Dashboard API Aggregation Endpoint | Backend service `DashboardService` &amp; endpoint `GET /api/v1/dashboard/overview`. |
| **Phase 5.6** | Dashboard Verification &amp; Integration | End-to-end integration testing and frontend-backend connectivity verification. |
