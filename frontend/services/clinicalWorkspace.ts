import { clearStoredToken, getAuthHeader } from "@/services/auth";
import { getApiBaseUrl } from "@/services/patients";
import type {
  CaseAnalysisPayload,
  ClinicalAnalysisRun,
  ClinicalCase,
  ClinicalCasePayload,
} from "@/types/clinicalWorkspace";
import type { ImagingAsset } from "@/types/imaging";

export class ClinicalWorkspaceApiError extends Error {
  readonly status: number;

  constructor(message: string, status = 0) {
    super(message);
    this.name = "ClinicalWorkspaceApiError";
    this.status = status;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...getAuthHeader(),
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...options.headers,
      },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Network error";
    throw new ClinicalWorkspaceApiError(
      `Could not reach the Arogya AI API at ${getApiBaseUrl()}. Check that the backend is running and allows this frontend origin in CORS settings (${message}).`,
    );
  }

  if (!response.ok) {
    if (response.status === 401) clearStoredToken();
    let message = `Clinical workspace request failed (${response.status}).`;
    try {
      const body: unknown = await response.json();
      if (body && typeof body === "object" && "detail" in body) {
        const detail = body.detail;
        if (typeof detail === "string") message = detail;
        else if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") {
          message = detail.message;
        } else if (Array.isArray(detail)) {
          message = detail.map((item: { msg?: string }) => item.msg || "Invalid input").join("; ");
        } else if (detail && typeof detail === "object" && "errors" in detail && Array.isArray(detail.errors)) {
          message = detail.errors.join(" ");
        }
      }
    } catch {
      // The response may be an empty or non-JSON error body.
    }
    throw new ClinicalWorkspaceApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function fetchPatientCases(patientId: string, signal?: AbortSignal): Promise<ClinicalCase[]> {
  return request<ClinicalCase[]>(`/patients/${encodeURIComponent(patientId)}/cases`, { signal });
}

export function createClinicalCase(
  patientId: string,
  payload: ClinicalCasePayload,
): Promise<ClinicalCase> {
  return request<ClinicalCase>(`/patients/${encodeURIComponent(patientId)}/cases`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateClinicalCase(
  caseId: string,
  payload: ClinicalCasePayload,
): Promise<ClinicalCase> {
  return request<ClinicalCase>(`/cases/${encodeURIComponent(caseId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function createCaseAnalysis(
  caseId: string,
  payload: CaseAnalysisPayload,
): Promise<ClinicalAnalysisRun> {
  return request<ClinicalAnalysisRun>(`/cases/${encodeURIComponent(caseId)}/analysis-runs`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function submitCaseAnalysis(runId: string): Promise<ClinicalAnalysisRun> {
  return request<ClinicalAnalysisRun>(`/analysis-runs/${encodeURIComponent(runId)}/submit`, {
    method: "POST",
  });
}

export function retryCaseAnalysis(runId: string): Promise<ClinicalAnalysisRun> {
  return request<ClinicalAnalysisRun>(`/analysis-runs/${encodeURIComponent(runId)}/retry`, {
    method: "POST",
  });
}

export function reviewCaseAnalysis(runId: string): Promise<ClinicalAnalysisRun> {
  return request<ClinicalAnalysisRun>(`/analysis-runs/${encodeURIComponent(runId)}/review`, {
    method: "POST",
  });
}

export function uploadCaseAttachment(
  patientId: string,
  caseId: string,
  file: File,
): Promise<ImagingAsset> {
  const form = new FormData();
  form.append("patient_id", patientId);
  form.append("encounter_id", caseId);
  form.append("file", file);
  return request<ImagingAsset>("/assets/upload", { method: "POST", body: form });
}

export function removeCaseAttachment(assetId: string): Promise<void> {
  return request<void>(`/assets/${encodeURIComponent(assetId)}`, { method: "DELETE" });
}

export async function downloadCaseAttachment(asset: ImagingAsset): Promise<void> {
  let response: Response;
  try {
    response = await fetch(
      `${getApiBaseUrl()}/assets/${encodeURIComponent(asset.id)}/download`,
      { headers: { Accept: asset.media_type, ...getAuthHeader() } },
    );
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Network error";
    throw new ClinicalWorkspaceApiError(`Could not download attachment (${message}).`);
  }
  if (!response.ok) {
    if (response.status === 401) clearStoredToken();
    throw new ClinicalWorkspaceApiError(`Could not download attachment (${response.status}).`, response.status);
  }
  const url = URL.createObjectURL(await response.blob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = asset.original_filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
