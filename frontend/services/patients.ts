/**
 * Arogya AI — Patient Intelligence API Client Service
 *
 * Module 6: Patient Intelligence.
 * Communicates with FastAPI backend for:
 * - Patient CRUD, search, filtering, and pagination
 * - Encounter creation and lifecycle updates
 * - Clinical observations and vitals recording
 * - Data quality evaluation and consistency warnings
 * - Longitudinal patient timeline stream
 */

import type {
  AnalysisRun,
  DataQualityReport,
  Encounter,
  EncounterCreatePayload,
  EncounterUpdatePayload,
  Observation,
  ObservationCreatePayload,
  PaginatedResponse,
  Patient,
  PatientCreatePayload,
  PatientTimelineResponse,
  PatientUpdatePayload,
} from "@/types/patients";
import { getAuthHeader, clearStoredToken } from "@/services/auth";

export class PatientsApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(message: string, status: number = 0, code: string = "API_ERROR", details?: unknown) {
    super(message);
    this.name = "PatientsApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get isNotFound(): boolean {
    return this.status === 404 || this.code === "RESOURCE_NOT_FOUND";
  }

  get isConflict(): boolean {
    return this.status === 409 || this.code === "CONFLICT";
  }

  get isValidationError(): boolean {
    return this.status === 422 || this.code === "VALIDATION_ERROR";
  }

  get isUnavailable(): boolean {
    return this.status === 503 || this.code === "SERVICE_UNAVAILABLE";
  }

  get isUnauthorized(): boolean {
    return this.status === 401 || this.code === "UNAUTHORIZED";
  }

  get isForbidden(): boolean {
    return this.status === 403 || this.code === "FORBIDDEN";
  }
}

export function getApiBaseUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8000/api/v1";
}

async function requestJson<T>(
  endpoint: string,
  options: RequestInit & { baseUrl?: string } = {}
): Promise<T> {
  const { baseUrl, ...fetchInit } = options;
  const base = (baseUrl || getApiBaseUrl()).replace(/\/+$/, "");
  const url = `${base}${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...fetchInit,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...getAuthHeader(),
        ...fetchInit.headers,
      },
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new PatientsApiError("Request was cancelled or timed out.", 408, "TIMEOUT");
    }
    const message = err instanceof Error ? err.message : "Network error";
    throw new PatientsApiError(
      `Failed to connect to backend (${message}). Verify that the Arogya AI backend is running.`,
      0,
      "NETWORK_ERROR"
    );
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredToken();
    }
    let errorCode = `HTTP_${response.status}`;
    let errorMessage = `Request failed with status ${response.status} (${response.statusText}).`;
    let details: unknown = undefined;

    try {
      const data = await response.json();
      if (data && typeof data === "object") {
        details = data;
        if (data.error && typeof data.error === "object") {
          errorCode = data.error.code || errorCode;
          errorMessage = data.error.message || errorMessage;
        } else if (typeof data.detail === "string") {
          errorMessage = data.detail;
        } else if (Array.isArray(data.detail)) {
          errorMessage = data.detail.map((d: { msg?: string }) => d.msg || "Invalid value").join("; ");
        }
      }
    } catch {
      // response body was not json
    }

    throw new PatientsApiError(errorMessage, response.status, errorCode, details);
  }

  return (await response.json()) as T;
}

// -----------------------------------------------------------------------------
// Patient Cohort Operations
// -----------------------------------------------------------------------------

export interface FetchPatientsParams {
  search?: string | null;
  biological_sex?: string | null;
  is_synthetic?: boolean | null;
  page?: number;
  page_size?: number;
  signal?: AbortSignal;
  baseUrl?: string;
}

export async function fetchPatients(
  params: FetchPatientsParams = {}
): Promise<PaginatedResponse<Patient>> {
  const searchParams = new URLSearchParams();
  if (params.search && params.search.trim()) {
    searchParams.set("search", params.search.trim());
  }
  if (params.biological_sex && params.biological_sex !== "all") {
    searchParams.set("biological_sex", params.biological_sex);
  }
  if (params.is_synthetic !== undefined && params.is_synthetic !== null) {
    searchParams.set("is_synthetic", String(params.is_synthetic));
  }
  if (params.page) {
    searchParams.set("page", String(params.page));
  }
  if (params.page_size) {
    searchParams.set("page_size", String(params.page_size));
  }

  const query = searchParams.toString();
  const endpoint = `/patients${query ? `?${query}` : ""}`;
  return requestJson<PaginatedResponse<Patient>>(endpoint, {
    method: "GET",
    signal: params.signal,
    baseUrl: params.baseUrl,
  });
}

export async function createPatient(
  payload: PatientCreatePayload,
  options: { signal?: AbortSignal; baseUrl?: string } = {}
): Promise<Patient> {
  return requestJson<Patient>("/patients", {
    method: "POST",
    body: JSON.stringify(payload),
    signal: options.signal,
    baseUrl: options.baseUrl,
  });
}

export async function fetchPatient(
  patientId: string,
  options: { signal?: AbortSignal; baseUrl?: string } = {}
): Promise<Patient> {
  return requestJson<Patient>(`/patients/${encodeURIComponent(patientId)}`, {
    method: "GET",
    signal: options.signal,
    baseUrl: options.baseUrl,
  });
}

export async function updatePatient(
  patientId: string,
  payload: PatientUpdatePayload,
  options: { signal?: AbortSignal; baseUrl?: string } = {}
): Promise<Patient> {
  return requestJson<Patient>(`/patients/${encodeURIComponent(patientId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
    signal: options.signal,
    baseUrl: options.baseUrl,
  });
}

// -----------------------------------------------------------------------------
// Data Quality & Timeline
// -----------------------------------------------------------------------------

export async function fetchPatientQuality(
  patientId: string,
  options: { signal?: AbortSignal; baseUrl?: string } = {}
): Promise<DataQualityReport> {
  return requestJson<DataQualityReport>(`/patients/${encodeURIComponent(patientId)}/quality`, {
    method: "GET",
    signal: options.signal,
    baseUrl: options.baseUrl,
  });
}

export async function fetchPatientTimeline(
  patientId: string,
  options: { limit?: number; signal?: AbortSignal; baseUrl?: string } = {}
): Promise<PatientTimelineResponse> {
  const query = options.limit ? `?limit=${options.limit}` : "";
  return requestJson<PatientTimelineResponse>(
    `/patients/${encodeURIComponent(patientId)}/timeline${query}`,
    {
      method: "GET",
      signal: options.signal,
      baseUrl: options.baseUrl,
    }
  );
}

// -----------------------------------------------------------------------------
// Encounters Operations
// -----------------------------------------------------------------------------

export async function fetchPatientEncounters(
  patientId: string,
  options: { status?: string; page?: number; page_size?: number; signal?: AbortSignal; baseUrl?: string } = {}
): Promise<PaginatedResponse<Encounter>> {
  const searchParams = new URLSearchParams();
  if (options.status && options.status !== "all") {
    searchParams.set("status", options.status);
  }
  if (options.page) {
    searchParams.set("page", String(options.page));
  }
  if (options.page_size) {
    searchParams.set("page_size", String(options.page_size));
  }

  const query = searchParams.toString();
  return requestJson<PaginatedResponse<Encounter>>(
    `/patients/${encodeURIComponent(patientId)}/encounters${query ? `?${query}` : ""}`,
    {
      method: "GET",
      signal: options.signal,
      baseUrl: options.baseUrl,
    }
  );
}

export async function createPatientEncounter(
  patientId: string,
  payload: EncounterCreatePayload,
  options: { signal?: AbortSignal; baseUrl?: string } = {}
): Promise<Encounter> {
  return requestJson<Encounter>(`/patients/${encodeURIComponent(patientId)}/encounters`, {
    method: "POST",
    body: JSON.stringify(payload),
    signal: options.signal,
    baseUrl: options.baseUrl,
  });
}

export async function updateEncounter(
  encounterId: string,
  payload: EncounterUpdatePayload,
  options: { signal?: AbortSignal; baseUrl?: string } = {}
): Promise<Encounter> {
  return requestJson<Encounter>(`/encounters/${encodeURIComponent(encounterId)}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
    signal: options.signal,
    baseUrl: options.baseUrl,
  });
}

// -----------------------------------------------------------------------------
// Observations Operations
// -----------------------------------------------------------------------------

export async function fetchEncounterObservations(
  encounterId: string,
  options: { page?: number; page_size?: number; signal?: AbortSignal; baseUrl?: string } = {}
): Promise<PaginatedResponse<Observation>> {
  const searchParams = new URLSearchParams();
  if (options.page) searchParams.set("page", String(options.page));
  if (options.page_size) searchParams.set("page_size", String(options.page_size));

  const query = searchParams.toString();
  return requestJson<PaginatedResponse<Observation>>(
    `/encounters/${encodeURIComponent(encounterId)}/observations${query ? `?${query}` : ""}`,
    {
      method: "GET",
      signal: options.signal,
      baseUrl: options.baseUrl,
    }
  );
}

export async function createEncounterObservation(
  encounterId: string,
  payload: ObservationCreatePayload,
  options: { signal?: AbortSignal; baseUrl?: string } = {}
): Promise<Observation> {
  return requestJson<Observation>(
    `/encounters/${encodeURIComponent(encounterId)}/observations`,
    {
      method: "POST",
      body: JSON.stringify(payload),
      signal: options.signal,
      baseUrl: options.baseUrl,
    }
  );
}

export async function fetchPatientObservations(
  patientId: string,
  options: { code?: string; page?: number; page_size?: number; signal?: AbortSignal; baseUrl?: string } = {}
): Promise<PaginatedResponse<Observation>> {
  const searchParams = new URLSearchParams();
  if (options.code) searchParams.set("code", options.code);
  if (options.page) searchParams.set("page", String(options.page));
  if (options.page_size) searchParams.set("page_size", String(options.page_size));

  const query = searchParams.toString();
  return requestJson<PaginatedResponse<Observation>>(
    `/patients/${encodeURIComponent(patientId)}/observations${query ? `?${query}` : ""}`,
    {
      method: "GET",
      signal: options.signal,
      baseUrl: options.baseUrl,
    }
  );
}

export async function fetchPatientAnalysisRuns(
  patientId: string,
  options: { status?: string; page?: number; page_size?: number; signal?: AbortSignal; baseUrl?: string } = {}
): Promise<PaginatedResponse<AnalysisRun>> {
  const searchParams = new URLSearchParams();
  if (options.status) searchParams.set("status", options.status);
  if (options.page) searchParams.set("page", String(options.page));
  if (options.page_size) searchParams.set("page_size", String(options.page_size));

  const query = searchParams.toString();
  return requestJson<PaginatedResponse<AnalysisRun>>(
    `/patients/${encodeURIComponent(patientId)}/analysis-runs${query ? `?${query}` : ""}`,
    {
      method: "GET",
      signal: options.signal,
      baseUrl: options.baseUrl,
    }
  );
}
