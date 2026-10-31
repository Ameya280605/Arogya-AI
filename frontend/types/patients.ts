/**
 * Arogya AI — Patient Intelligence TypeScript Contracts
 *
 * Module 6: Patient Intelligence.
 * Mirrors the backend Pydantic API schemas across patient cohorts,
 * clinical encounters, physiological observations, data quality, and timelines.
 */

export type BiologicalSex = "male" | "female" | "other" | "unknown";
export type EncounterType = "ambulatory" | "inpatient" | "emergency" | "synthetic";
export type EncounterStatus = "planned" | "in_progress" | "completed" | "cancelled";

export interface Patient {
  id: string;
  mrn_pseudonym: string;
  birth_date: string | null;
  biological_sex: BiologicalSex | null;
  is_synthetic: boolean;
  created_at: string;
  updated_at: string;
}

export interface PatientCreatePayload {
  mrn_pseudonym: string;
  birth_date?: string | null;
  biological_sex?: BiologicalSex | null;
  is_synthetic?: boolean;
}

export interface PatientUpdatePayload {
  birth_date?: string | null;
  biological_sex?: BiologicalSex | null;
  is_synthetic?: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface Encounter {
  id: string;
  patient_id: string;
  encounter_type: EncounterType;
  status: EncounterStatus;
  start_time: string;
  end_time: string | null;
  created_at: string;
  updated_at: string;
}

export interface EncounterCreatePayload {
  encounter_type: EncounterType;
  status: EncounterStatus;
  start_time: string;
  end_time?: string | null;
}

export interface EncounterUpdatePayload {
  encounter_type?: EncounterType;
  status?: EncounterStatus;
  start_time?: string;
  end_time?: string | null;
}

export interface Observation {
  id: string;
  encounter_id: string;
  patient_id: string;
  code: string;
  display_name: string;
  numeric_value: number | null;
  text_value: string | null;
  unit: string | null;
  observed_at: string;
  source_metadata?: Record<string, unknown> | null;
  created_at: string;
}

export interface ObservationCreatePayload {
  code: string;
  display_name: string;
  numeric_value?: number | null;
  text_value?: string | null;
  unit?: string | null;
  observed_at: string;
  source_metadata?: Record<string, unknown> | null;
}

export interface AnalysisRun {
  id: string;
  patient_id: string;
  encounter_id?: string | null;
  asset_id?: string | null;
  model_name: string;
  model_version: string;
  status: string;
  parameters?: Record<string, unknown> | null;
  results_summary?: Record<string, unknown> | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface DataQualityIssue {
  category: "demographic" | "clinical" | "unit" | "temporal";
  severity: "info" | "warning" | "critical";
  field?: string | null;
  message: string;
}

export interface DataQualityReport {
  patient_id: string;
  completeness_score: number;
  demographic_score: number;
  clinical_score: number;
  issues: DataQualityIssue[];
  has_warnings: boolean;
}

export interface PatientTimelineItem {
  id: string;
  event_type: "encounter" | "observation" | "analysis_run" | "audit_event";
  title: string;
  description?: string | null;
  timestamp: string;
  status?: string | null;
  metadata?: Record<string, unknown> | null;
}

export interface PatientTimelineResponse {
  patient_id: string;
  items: PatientTimelineItem[];
  total: number;
}
