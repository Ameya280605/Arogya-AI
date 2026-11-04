import type { AnalysisRun, Observation } from "@/types/patients";
import type { ImagingAsset } from "@/types/imaging";

export type ClinicalCaseStatus = "draft" | "planned" | "in_progress" | "completed" | "cancelled";
export type AnalysisLifecycleStatus = "draft" | "queued" | "running" | "completed" | "failed" | "needs_review";

export interface ClinicalMeasurement {
  kind: "vital" | "laboratory";
  code: string;
  display_name: string;
  numeric_value: number | null;
  text_value?: string | null;
  unit: string | null;
  reference_low?: number | null;
  reference_high?: number | null;
}

export interface CaseQuality {
  blocking_errors: string[];
  warnings: string[];
  ready_for_analysis: boolean;
}

export interface ClinicalCase {
  id: string;
  patient_id: string;
  encounter_type: string;
  status: ClinicalCaseStatus;
  start_time: string;
  end_time: string | null;
  symptoms: string | null;
  symptom_duration: string | null;
  medical_history: string | null;
  medications: string[];
  allergies: string[];
  clinical_notes: string | null;
  created_at: string;
  updated_at: string;
  observations: Observation[];
  attachments: ImagingAsset[];
  analysis_runs: ClinicalAnalysisRun[];
  quality: CaseQuality;
}

export interface ClinicalCasePayload {
  encounter_type?: "ambulatory" | "inpatient" | "emergency" | "synthetic";
  status?: ClinicalCaseStatus;
  symptoms?: string | null;
  symptom_duration?: string | null;
  medical_history?: string | null;
  medications?: string[];
  allergies?: string[];
  clinical_notes?: string | null;
  measurements?: ClinicalMeasurement[];
}

export interface CaseAnalysisPayload {
  analysis_type: "tabular" | "imaging";
  submit_now: boolean;
  tabular_input?: {
    age?: number;
    gender?: number;
    smoking?: number;
    imaginary_min?: number | null;
    imaginary_avg?: number | null;
    real_min?: number | null;
    real_avg?: number | null;
  };
  asset_id?: string;
  generate_heatmap?: boolean;
  heatmap_label?: string;
}

export type ClinicalAnalysisRun = AnalysisRun & {
  status: AnalysisLifecycleStatus | string;
  draft_input?: Record<string, unknown> | null;
  output_references?: Array<{ type: string; href: string }> | null;
  retry_count: number;
  updated_at?: string | null;
};
