import type { AnalysisRun } from "@/types/patients";

export interface ImagingAsset {
  id: string;
  patient_id: string;
  encounter_id: string | null;
  original_filename: string;
  media_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
  storage_path: string;
  created_at: string;
}

export interface ImagingInferenceRequest {
  asset_id: string;
  generate_heatmap: boolean;
  heatmap_label: string;
}

export interface ImagingPrediction {
  label: string;
  score: number;
}

export interface GradCAMResult {
  label: string;
  raw_model_score: number;
  research_only: boolean;
  note: string;
}

export interface ImagingResultSummary {
  predictions?: ImagingPrediction[];
  research_only?: boolean;
  disclaimer?: string;
  output_type?: string;
  gradcam?: GradCAMResult;
}

export interface ImagingAnalysisRun extends Omit<AnalysisRun, "results_summary"> {
  results_summary?: ImagingResultSummary | null;
}
