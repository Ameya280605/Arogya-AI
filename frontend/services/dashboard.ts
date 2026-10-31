/**
 * Arogya AI — Dashboard API Client Service
 *
 * Module 5, Phase 5.5: Dashboard API Aggregation & Integration.
 * Consumes the versioned FastAPI aggregation endpoint:
 *   GET /api/v1/dashboard/overview
 *
 * Provides typed requests, query parameter formatting, standard error
 * normalization, and honest handling of unavailable backend/database states.
 */

import type {
  AnalysisRunStatus,
  DashboardOverviewResponse,
} from "@/types/dashboard";
import { getAuthHeader, clearStoredToken } from "@/services/auth";

export interface DashboardApiFilterParams {
  /** Optional UTC Start date in YYYY-MM-DD format */
  startDate?: string | null;
  /** Optional UTC End date in YYYY-MM-DD format */
  endDate?: string | null;
  /** Optional analysis run status filter */
  status?: AnalysisRunStatus | "all" | null;
}

export interface FetchDashboardOptions {
  /** Filter criteria */
  filters?: DashboardApiFilterParams;
  /** Abort signal for request cancellation / timeout */
  signal?: AbortSignal;
  /** Optional base URL override (defaults to NEXT_PUBLIC_API_URL or local backend) */
  baseUrl?: string;
}

/**
 * Standardized client error for Dashboard API operations.
 */
export class DashboardApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(message: string, status: number = 0, code: string = "API_ERROR", details?: unknown) {
    super(message);
    this.name = "DashboardApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** True if the backend or database persistence layer is unconfigured or unreachable */
  get isUnavailable(): boolean {
    return this.status === 503 || this.code === "SERVICE_UNAVAILABLE";
  }

  /** True if the request failed due to parameter validation */
  get isValidationError(): boolean {
    return this.status === 422 || this.code === "VALIDATION_ERROR";
  }

  /** True if the request failed due to missing or invalid credentials */
  get isUnauthorized(): boolean {
    return this.status === 401 || this.code === "UNAUTHORIZED";
  }

  /** True if the request failed due to insufficient permissions */
  get isForbidden(): boolean {
    return this.status === 403 || this.code === "FORBIDDEN";
  }
}

/**
 * Resolve the canonical base API URL.
 */
export function getApiBaseUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8000/api/v1";
}

/**
 * Construct URL for GET /api/v1/dashboard/overview with query parameters.
 */
export function buildDashboardOverviewUrl(
  filters?: DashboardApiFilterParams,
  baseUrl?: string
): string {
  const base = (baseUrl || getApiBaseUrl()).replace(/\/+$/, "");
  const url = new URL(`${base}/dashboard/overview`);

  if (filters?.startDate && filters.startDate.trim() !== "") {
    url.searchParams.set("start_date", filters.startDate.trim());
  }

  if (filters?.endDate && filters.endDate.trim() !== "") {
    url.searchParams.set("end_date", filters.endDate.trim());
  }

  if (filters?.status && filters.status !== "all") {
    url.searchParams.set("status", filters.status);
  }

  return url.toString();
}

/**
 * Retrieve database-backed dashboard aggregate metrics from the backend API.
 *
 * @throws {DashboardApiError} On HTTP error responses or connection failures.
 */
export async function fetchDashboardOverview(
  options: FetchDashboardOptions = {}
): Promise<DashboardOverviewResponse> {
  const url = buildDashboardOverviewUrl(options.filters, options.baseUrl);

  let response: Response;
  try {
    response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...getAuthHeader(),
      },
      signal: options.signal,
    });
  } catch (err: unknown) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new DashboardApiError("Dashboard request timed out or was cancelled.", 408, "TIMEOUT");
    }
    const message = err instanceof Error ? err.message : "Network connection failure";
    throw new DashboardApiError(
      `Failed to connect to Arogya AI backend (${message}). Verify that the backend service is running.`,
      0,
      "NETWORK_ERROR"
    );
  }

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredToken();
    }
    let errorCode = `HTTP_${response.status}`;
    let errorMessage = `Dashboard API request failed with status ${response.status} (${response.statusText}).`;
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
        } else if (Array.isArray(data.detail) && data.detail[0]?.msg) {
          errorMessage = data.detail.map((d: { msg: string }) => d.msg).join("; ");
          errorCode = "VALIDATION_ERROR";
        }
      }
    } catch {
      // Body not JSON
    }

    throw new DashboardApiError(errorMessage, response.status, errorCode, details);
  }

  try {
    return (await response.json()) as DashboardOverviewResponse;
  } catch (parseErr) {
    throw new DashboardApiError(
      "Received malformed JSON payload from Dashboard API.",
      502,
      "MALFORMED_RESPONSE",
      parseErr
    );
  }
}
