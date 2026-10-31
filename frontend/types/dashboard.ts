/**
 * Arogya AI — Dashboard Data Contracts (TypeScript Definitions)
 *
 * Module 5, Phase 5.1: Dashboard Data Contracts.
 * Mirrors the canonical Pydantic schemas in `backend/app/schemas/dashboard.py`.
 *
 * Canonical Source of Truth: `backend/app/schemas/dashboard.py`
 *
 * Governance:
 * - Types define read-only response contracts for Overview Dashboard presentation.
 * - Non-negative counts, UTC ISO 8601 string timestamps.
 * - Zero PHI tolerance: summaries strictly exclude patient names, credentials, and diagnostic text.
 */

export type AnalysisRunStatus = "queued" | "running" | "completed" | "failed" | "abstained";

/**
 * Patient cohort summary counts.
 */
export interface PatientSummary {
  /** Total registered patient profiles across synthetic and research cohorts */
  total_patients: number;
  /** Count of artificially generated synthetic patient profiles */
  synthetic_patients: number;
  /** Count of licensed/de-identified research dataset patient profiles */
  research_cohort_patients: number;
  /** Timestamp in UTC ISO 8601 when patient counts were computed */
  generated_at: string;
}

/**
 * Clinical encounter metrics and status breakdown.
 */
export interface EncounterSummary {
  /** Total recorded clinical encounters across all statuses */
  total_encounters: number;
  /** Count of encounters scheduled or planned */
  planned: number;
  /** Count of encounters currently active or underway */
  in_progress: number;
  /** Count of successfully concluded encounters */
  completed: number;
  /** Count of cancelled or aborted encounters */
  cancelled: number;
  /** Optional commencement timestamp of encounter aggregation window in UTC */
  reporting_period_start?: string | null;
  /** Optional conclusion timestamp of encounter aggregation window in UTC */
  reporting_period_end?: string | null;
  /** Timestamp in UTC ISO 8601 when encounter counts were computed */
  generated_at: string;
}

/**
 * Status distribution breakdown for AI model analysis executions.
 */
export interface AnalysisStatusBreakdown {
  /** Analysis runs queued awaiting compute worker dispatch */
  queued: number;
  /** Analysis runs actively executing inference pipelines */
  running: number;
  /** Analysis runs successfully completed with research findings */
  completed: number;
  /** Analysis runs terminated abnormally due to runtime errors */
  failed: number;
  /** Analysis runs abstained due to high entropy, uncertainty, or safety filters */
  abstained: number;
}

/**
 * Aggregate analysis run metrics for overview dashboard.
 */
export interface AnalysisSummary {
  /** Total analysis runs recorded across all execution states */
  total_runs: number;
  /** Detailed execution status breakdown */
  by_status: AnalysisStatusBreakdown;
  /** List of distinct model identifiers observed in the current analysis registry */
  active_models_observed: string[];
  /** Timestamp in UTC ISO 8601 when analysis metrics were generated */
  generated_at: string;
}

/**
 * Representation of an analysis run or finding candidate awaiting clinical review.
 */
export interface PendingReviewItem {
  /** Analysis run UUID identifying the evaluated output */
  run_id: string;
  /** Patient UUID associated with the pending analysis */
  patient_id: string;
  /** Optional encounter UUID context */
  encounter_id?: string | null;
  /** Canonical identifier of the model that produced findings */
  model_name: string;
  /** Version of the model that executed the analysis */
  model_version: string;
  /** Analysis lifecycle state (e.g. 'completed' or 'abstained') */
  status: string;
  /** True if model abstained due to safety checks or high uncertainty */
  abstained: boolean;
  /** Timestamp when the analysis run was created in UTC ISO 8601 */
  created_at: string;
}

/**
 * Pending clinical review queue metrics and preview for the overview dashboard.
 */
export interface PendingReviewQueueSummary {
  /** Total number of completed or abstained analysis runs awaiting clinician review */
  pending_count: number;
  /** Preview of pending review items bounded for overview presentation */
  items: PendingReviewItem[];
  /** Timestamp in UTC ISO 8601 when review queue was summarized */
  generated_at: string;
}

/**
 * Sanitized, non-PHI summary of a recent system or research event.
 */
export interface RecentActivityItem {
  /** Unique identifier of the audit event or activity record */
  id: string;
  /** Classification of event (e.g. 'analysis.started', 'user.login', 'case.created') */
  event_type: string;
  /** Action category ('create', 'read', 'update', 'delete', 'execute') */
  action: string;
  /** Target resource category ('patient', 'encounter', 'asset', 'analysis_run') */
  resource_type?: string | null;
  /** Identifier of target resource (e.g. UUID string or pseudonym) */
  resource_id?: string | null;
  /** Safe, human-readable event summary omitting sensitive clinical or credential data */
  description?: string | null;
  /** Event recording timestamp in UTC ISO 8601 */
  timestamp: string;
}

/**
 * Recent system activity feed for the overview dashboard.
 */
export interface RecentActivitySummary {
  /** Total audit events recorded in the observed activity window */
  total_events: number;
  /** Chronological sequence of recent system activity items (most recent first) */
  activities: RecentActivityItem[];
  /** Timestamp in UTC ISO 8601 when recent activity was summarized */
  generated_at: string;
}

/**
 * Composed data contract for the Arogya AI Overview Dashboard.
 */
export interface DashboardOverviewResponse {
  /** Patient cohort summary counts */
  patients: PatientSummary;
  /** Clinical encounter summary counts */
  encounters: EncounterSummary;
  /** AI analysis run totals and status breakdowns */
  analysis: AnalysisSummary;
  /** Pending clinical review queue metrics */
  reviews: PendingReviewQueueSummary;
  /** Recent platform activity entries */
  recent_activity: RecentActivitySummary;
  /** UTC ISO 8601 timestamp when the complete dashboard payload was composed */
  generated_at: string;
  /** Runtime environment identifier ('development', 'testing', 'staging', 'production') */
  environment: string;
}
