# Arogya AI — Dashboard Data Contracts Specification

> **Module:** Module 5 (Overview Dashboard)<br/>
> **Phase:** 5.1 (Dashboard Data Contracts)<br/>
> **Status:** Specification Complete<br/>
> **Canonical Source of Truth:** [`backend/app/schemas/dashboard.py`](file:///C:/_code/Projects/Arogya-AI/backend/app/schemas/dashboard.py)<br/>
> **Frontend Contract Mirror:** [`frontend/types/dashboard.ts`](file:///C:/_code/Projects/Arogya-AI/frontend/types/dashboard.ts)

---

## 1. Overview & Architectural Principles

Phase 5.1 defines the strongly-typed, validated response data contracts for the Arogya AI Overview Dashboard. In accordance with the canonical roadmap ([MODULE_DEPENDENCIES.md](file:///C:/_code/Projects/Arogya-AI/docs/architecture/MODULE_DEPENDENCIES.md)), the Overview Dashboard aggregates high-level platform status across five logical domains:

1. **Patient Cohort Summary:** Counts of registered research and synthetic patient subjects.
2. **Clinical Encounter Summary:** Status breakdown of scheduled, active, and completed encounters.
3. **AI Analysis Run Summary:** Execution metrics, active model tracking, and status distributions across AI inference pipelines.
4. **Pending Clinical Review Queue:** Triage counts and candidate previews of analysis runs awaiting clinician review.
5. **Recent Platform Activity:** Sanitized audit telemetry providing operational accountability.

### Architectural Tenets
- **Strict Boundary Decoupling:** Contracts represent pure, validated Pydantic models with `extra="forbid"`. They do not leak internal database implementation details, session handles, or raw SQL queries.
- **Non-Negative Value Constraints:** All integer metrics and counts enforce `ge=0`. Negative values fail validation immediately.
- **Timezone Awareness:** All timestamps (`generated_at`, `start_time`, `timestamp`) must be explicit UTC ISO 8601 strings; naive datetimes are rejected.
- **Zero-PHI Guarantee:** Contracts strictly forbid patient identifiable information (PHI/PII), plaintext credentials, session tokens, or unstructured clinical narrative text.
- **Honest States & No Fabricated Metrics:** Unbuilt clinical workflows (such as formal doctor sign-offs) are accurately framed as candidate previews derived from existing models rather than fabricated database structures.

---

## 2. Response Contracts Specification

### A. Patient Summary (`PatientSummary`)
Aggregates cohort metrics representing the patient subjects registered within the system.

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `total_patients` | `int` | `ge=0` | Total registered patient profiles across all cohorts. |
| `synthetic_patients` | `int` | `ge=0` | Count of artificially generated synthetic patient profiles. |
| `research_cohort_patients` | `int` | `ge=0` | Count of licensed/de-identified research dataset patient profiles. |
| `generated_at` | `datetime` | UTC aware | Timestamp when patient cohort metrics were computed. |

*Validation Rule:* `total_patients` must equal `synthetic_patients + research_cohort_patients`.

---

### B. Encounter Summary (`EncounterSummary`)
Aggregates clinical encounters across care interaction classifications.

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `total_encounters` | `int` | `ge=0` | Total recorded clinical encounters across all statuses. |
| `planned` | `int` | `ge=0, default=0` | Count of encounters scheduled or planned. |
| `in_progress` | `int` | `ge=0, default=0` | Count of encounters currently active or underway. |
| `completed` | `int` | `ge=0, default=0` | Count of successfully concluded encounters. |
| `cancelled` | `int` | `ge=0, default=0` | Count of cancelled or aborted encounters. |
| `reporting_period_start` | `datetime \| None` | Optional UTC | Commencement timestamp of encounter aggregation window. |
| `reporting_period_end` | `datetime \| None` | Optional UTC | Conclusion timestamp of encounter aggregation window. |
| `generated_at` | `datetime` | UTC aware | Timestamp when encounter metrics were computed. |

*Validation Rules:*
- `total_encounters` must equal `planned + in_progress + completed + cancelled`.
- If both `reporting_period_start` and `reporting_period_end` are specified, `reporting_period_end >= reporting_period_start`.

---

### C. Analysis Summary (`AnalysisSummary`)
Captures aggregate execution metrics and lifecycle status breakdowns for research AI model runs.

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `total_runs` | `int` | `ge=0` | Total analysis runs recorded across all execution states. |
| `by_status` | `AnalysisStatusBreakdown` | Sub-schema | Execution status distribution breakdown. |
| `active_models_observed` | `list[str]` | Default `[]` | List of distinct canonical model names observed in registry. |
| `generated_at` | `datetime` | UTC aware | Timestamp when analysis metrics were generated. |

#### Sub-Schema: `AnalysisStatusBreakdown`
Reuses the exact lifecycle states defined by `AnalysisRun.status` in the relational schema:
- `queued`: Runs awaiting compute worker dispatch.
- `running`: Runs actively executing inference pipelines.
- `completed`: Runs successfully completed with research findings.
- `failed`: Runs terminated abnormally due to runtime errors.
- `abstained`: Runs where the model triggered automated abstention due to high entropy, uncertainty, or safety filter triggers.

*Validation Rule:* `total_runs` must equal `queued + running + completed + failed + abstained`.

---

### D. Pending Review Queue (`PendingReviewQueueSummary`)
Provides clinical review metrics and a bounded candidate preview for human-in-the-loop oversight.

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `pending_count` | `int` | `ge=0` | Total candidate analysis runs awaiting clinician review. |
| `items` | `list[PendingReviewItem]` | Default `[]` | Top queue items bounded for overview presentation (typically 5–10). |
| `generated_at` | `datetime` | UTC aware | Timestamp when the review queue was summarized. |

#### Sub-Schema: `PendingReviewItem`
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `run_id` | `UUID` | Unique analysis run identifier. |
| `patient_id` | `UUID` | Associated patient UUID. |
| `encounter_id` | `UUID \| None` | Optional associated clinical encounter identifier. |
| `model_name` | `str` | Model identifier that generated findings. |
| `model_version` | `str` | Version tag of the model. |
| `status` | `str` | Analysis lifecycle state (e.g. `completed`, `abstained`). |
| `abstained` | `bool` | True if the model abstained due to safety/entropy filters. |
| `created_at` | `datetime` | Timestamp when the analysis task was submitted. |

#### Paginated Envelope: `PendingReviewQueuePaginated`
Specializes `PaginatedResponse[PendingReviewItem]` to support full paginated review queue endpoints (`page`, `page_size`, `total`, `items`).

---

### E. Recent System Activity (`RecentActivitySummary`)
Sanitized, non-PHI summary of recent operational audit events and pipeline executions.

| Field Name | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `total_events` | `int` | `ge=0` | Total audit events recorded in the observed activity window. |
| `activities` | `list[RecentActivityItem]` | Default `[]` | Chronological sequence of recent system activity items (newest first). |
| `generated_at` | `datetime` | UTC aware | Timestamp when recent activity was summarized. |

#### Sub-Schema: `RecentActivityItem`
| Field Name | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Unique audit event identifier. |
| `event_type` | `str` | Action classification (e.g. `'analysis.started'`, `'user.login'`, `'case.created'`). |
| `action` | `str` | Action category (`'create'`, `'read'`, `'update'`, `'delete'`, `'execute'`). |
| `resource_type` | `str \| None` | Target resource classification (`'patient'`, `'encounter'`, `'analysis_run'`). |
| `resource_id` | `str \| None` | Safe resource identifier (pseudonym or UUID string). |
| `description` | `str \| None` | Safe, human-readable summary description. |
| `timestamp` | `datetime` | Timestamp when event was recorded in UTC. |

---

### F. Composed Dashboard Overview (`DashboardOverviewResponse`)
Aggregates all five summary sections into a unified contract for the `/` overview dashboard view.

```python
class DashboardOverviewResponse(BaseSchema):
    patients: PatientSummary
    encounters: EncounterSummary
    analysis: AnalysisSummary
    reviews: PendingReviewQueueSummary
    recent_activity: RecentActivitySummary
    generated_at: datetime
    environment: str = "development"
```

---

## 3. Existing Database Support & Gap Analysis

| Logical Contract | Underlying Entity & Repository Support | Identified Gaps / Deferred Capabilities |
| :--- | :--- | :--- |
| **Patient Summary** | `Patient` model; `PatientRepository.count_patients(is_synthetic=...)` | Aggregation query grouping counts across synthetic vs licensed cohorts will be encapsulated in `DashboardService` during Phase 5.2. |
| **Encounter Summary** | `Encounter` model; `EncounterRepository` tracks `status` | Repository currently provides `count_by_patient`; system-wide group-by query across all encounters will be implemented in `DashboardRepository` / `DashboardService` in Phase 5.2. |
| **Analysis Summary** | `AnalysisRun` model; `AnalysisRepository` tracks status | Existing statuses (`queued`, `running`, `completed`, `failed`, `abstained`) map 1:1. System-wide status group-by aggregation to be added in Phase 5.2. |
| **Review Queue** | `AnalysisRun` model with status `completed` or `abstained` | **Architectural Gap:** Formal `Review` entity, reviewer assignment, doctor sign-offs, and amendment logs are deferred to Module 15 (Doctor Review & Feedback). Currently, pending review items are derived directly from unreviewed completed/abstained `AnalysisRun` records. |
| **Recent Activity** | `AuditEvent` model; `AuditRepository.list_events()` | `AuditEvent` table directly supports `event_type`, `action`, `resource_type`, `description`, `created_at`. No database schema modifications needed. |

---

## 4. Synthetic Data Provenance & Safety Tenets

1. **Development & Seed Provenance:** In Module 3 (Phase 3.5), synthetic seed records were established (`SYNTH-PAT-0001` through `SYNTH-PAT-0010`). All dashboard counts and preview items in development represent synthetic subjects or de-identified public research datasets.
2. **Zero-PHI Compliance:** Summaries strictly omit patient names, birth dates, postal addresses, phone numbers, and unstructured clinical notes.
3. **No Fabricated Live Metrics:** Tests and contract definitions do not pretend that live EHR streams or production clinical pipelines are active.
4. **Clinical Safety Tenet:** Overview dashboard statistics represent investigative research prototype metrics and must **never** be interpreted as clinical quality indicators or autonomous triage decisions.

---

## 5. Frontend Alignment & Future Integration

- **TypeScript Definitions:** Maintained in [`frontend/types/dashboard.ts`](file:///C:/_code/Projects/Arogya-AI/frontend/types/dashboard.ts) matching Python Pydantic models.
- **Phase 5.2 Implementation (Summary Cards & Recent Activity):** Delivered reusable UI components in [`frontend/components/dashboard/`](file:///C:/_code/Projects/Arogya-AI/frontend/components/dashboard/) (`SummaryCard`, `PatientSummaryCard`, `EncounterSummaryCard`, `AnalysisSummaryCard`, `ReviewQueueSummaryCard`, `RecentActivityFeed`). Integrated into `/` overview page with truthful unavailable and synthetic demonstration states. See [`docs/dashboard/SUMMARY_CARDS_AND_ACTIVITY.md`](file:///C:/_code/Projects/Arogya-AI/docs/dashboard/SUMMARY_CARDS_AND_ACTIVITY.md).
- **Roadmap Phase Reconciliation:** The Phase 5.1 completion report proposed backend aggregation in 5.2; however, the canonical roadmap assigned Phase 5.2 to frontend Summary Cards & Recent Activity UI components. Backend aggregation queries and HTTP routes are scheduled for Phase 5.3.
- **Phase 5.3 Integration:** Backend `DashboardService`, aggregation queries, and FastAPI router mounted under `/api/v1/dashboard/overview` will expose `DashboardOverviewResponse` via OpenAPI documentation and connect live data to the frontend dashboard.
