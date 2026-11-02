import { clearStoredToken, getAuthHeader } from "@/services/auth";
import { getApiBaseUrl } from "@/services/patients";
import type {
  ImagingAnalysisRun,
  ImagingAsset,
  ImagingInferenceRequest,
} from "@/types/imaging";

export class ImagingApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status = 0, code = "API_ERROR") {
    super(message);
    this.name = "ImagingApiError";
    this.status = status;
    this.code = code;
  }
}

function getErrorMessage(data: unknown, fallback: string): string {
  if (!data || typeof data !== "object") return fallback;

  const body = data as {
    detail?: unknown;
    error?: { message?: unknown; code?: unknown };
  };
  if (typeof body.error?.message === "string") return body.error.message;
  if (typeof body.detail === "string") return body.detail;
  if (Array.isArray(body.detail)) {
    return body.detail
      .map((item: { msg?: string }) => item.msg || "Invalid request")
      .join("; ");
  }
  return fallback;
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
      ...options,
      headers: {
        Accept: "application/json",
        ...getAuthHeader(),
        ...options.headers,
      },
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Network error";
    throw new ImagingApiError(
      `Could not connect to the Arogya AI backend (${message}).`,
      0,
      "NETWORK_ERROR"
    );
  }

  if (!response.ok) {
    if (response.status === 401) clearStoredToken();

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    throw new ImagingApiError(
      getErrorMessage(data, `Imaging request failed (${response.status}).`),
      response.status,
      `HTTP_${response.status}`
    );
  }

  return (await response.json()) as T;
}

export function fetchPatientImagingAssets(
  patientId: string,
  signal?: AbortSignal
): Promise<ImagingAsset[]> {
  return request<ImagingAsset[]>(
    `/patients/${encodeURIComponent(patientId)}/assets`,
    { method: "GET", signal }
  );
}

export function executeImagingAnalysis(
  patientId: string,
  payload: ImagingInferenceRequest
): Promise<ImagingAnalysisRun> {
  return request<ImagingAnalysisRun>(
    `/patients/${encodeURIComponent(patientId)}/analysis/imaging`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function fetchImagingHeatmap(
  runId: string,
  signal?: AbortSignal
): Promise<Blob> {
  let response: Response;
  try {
    response = await fetch(
      `${getApiBaseUrl()}/analysis-runs/${encodeURIComponent(runId)}/imaging/heatmap`,
      {
        method: "GET",
        signal,
        headers: {
          Accept: "image/png",
          ...getAuthHeader(),
        },
      }
    );
  } catch (error: unknown) {
    if (error instanceof Error && error.name === "AbortError") throw error;
    const message = error instanceof Error ? error.message : "Network error";
    throw new ImagingApiError(
      `Could not retrieve the Grad-CAM heatmap (${message}).`,
      0,
      "NETWORK_ERROR"
    );
  }

  if (!response.ok) {
    if (response.status === 401) clearStoredToken();
    throw new ImagingApiError(
      `Could not retrieve the Grad-CAM heatmap (${response.status}).`,
      response.status,
      `HTTP_${response.status}`
    );
  }

  return response.blob();
}
