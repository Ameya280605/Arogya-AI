/**
 * Arogya AI — Authentication and Session Service
 *
 * Module 7: Security, Identity & File Handling.
 * Handles client-side JWT token storage, login/logout operations,
 * session retrieval, and automated Authorization header injection.
 */

import { useSyncExternalStore } from "react";

export interface UserSummary {
  id: string;
  username?: string;
  email: string;
  full_name: string | null;
  role?: string;
  roles?: string[];
  permissions?: string[];
  is_active: boolean;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserSummary;
}

export interface LoginPayload {
  username: string;
  password: string;
}

export class AuthApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details?: unknown;

  constructor(message: string, status: number = 0, code: string = "AUTH_ERROR", details?: unknown) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const TOKEN_STORAGE_KEY = "arogya_ai_token";
const USER_STORAGE_KEY = "arogya_ai_user";

// In-memory cached snapshots and raw strings to guarantee stable references for React useSyncExternalStore
let cachedRawToken: string | null = null;
let cachedTokenSnapshot: string | null = null;

let cachedRawUser: string | null = null;
let cachedUserSnapshot: UserSummary | null = null;

// Subscribers for React useSyncExternalStore and external listeners
type AuthListener = (user: UserSummary | null) => void;
const authListeners = new Set<AuthListener>();
const storeSubscribers = new Set<() => void>();

function notifySubscribers(): void {
  const currentUser = getStoredUser();

  // 1. Notify React useSyncExternalStore subscribers
  storeSubscribers.forEach((subscriber) => {
    try {
      subscriber();
    } catch (err) {
      console.error("Error in auth store subscriber:", err);
    }
  });

  // 2. Notify onAuthChange listeners
  authListeners.forEach((listener) => {
    try {
      listener(currentUser);
    } catch (err) {
      console.error("Error in onAuthChange listener:", err);
    }
  });

  // 3. Dispatch window CustomEvent for cross-module or global listeners
  if (typeof window !== "undefined") {
    try {
      window.dispatchEvent(
        new CustomEvent("arogya_ai_auth_change", {
          detail: { user: currentUser, token: cachedTokenSnapshot },
        })
      );
    } catch {
      // Ignore
    }
  }
}

// Multi-tab synchronization via browser storage events
if (typeof window !== "undefined") {
  window.addEventListener("storage", (event: StorageEvent) => {
    if (
      event.key === USER_STORAGE_KEY ||
      event.key === TOKEN_STORAGE_KEY ||
      event.key === null
    ) {
      // Invalidate raw cached markers so getStoredUser/getStoredToken re-read and parse once
      cachedRawToken = null;
      cachedRawUser = null;
      notifySubscribers();
    }
  });
}

export function getApiBaseUrl(): string {
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  return "http://127.0.0.1:8000/api/v1";
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage ? window.localStorage.getItem(TOKEN_STORAGE_KEY) : null;
    if (raw === null || raw === "undefined" || raw === "null" || raw.trim() === "") {
      cachedRawToken = null;
      cachedTokenSnapshot = null;
      return null;
    }
    if (raw === cachedRawToken && cachedTokenSnapshot !== null) {
      return cachedTokenSnapshot;
    }
    cachedRawToken = raw;
    cachedTokenSnapshot = raw;
    return cachedTokenSnapshot;
  } catch {
    return cachedTokenSnapshot;
  }
}

export function onAuthChange(callback: (user: UserSummary | null) => void): () => void {
  authListeners.add(callback);
  return () => {
    authListeners.delete(callback);
  };
}

export function setStoredToken(token: string): void {
  cachedTokenSnapshot = token;
  cachedRawToken = token;
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } catch {
      // Ignore localStorage write failures (e.g. private browsing quota)
    }
  }
  notifySubscribers();
}

export function clearStoredToken(): void {
  cachedTokenSnapshot = null;
  cachedRawToken = null;
  cachedUserSnapshot = null;
  cachedRawUser = null;
  if (typeof window !== "undefined" && window.localStorage) {
    try {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
      window.localStorage.removeItem(USER_STORAGE_KEY);
    } catch {
      // Ignore
    }
  }
  notifySubscribers();
}

export function getStoredUser(): UserSummary | null {
  if (typeof window === "undefined") {
    return null;
  }
  try {
    const raw = window.localStorage ? window.localStorage.getItem(USER_STORAGE_KEY) : null;
    if (raw === null || raw === "undefined" || raw === "null" || raw.trim() === "") {
      cachedRawUser = null;
      cachedUserSnapshot = null;
      return null;
    }
    // Return the cached reference if the serialized representation in localStorage hasn't changed
    if (raw === cachedRawUser && cachedUserSnapshot !== null) {
      return cachedUserSnapshot;
    }
    cachedRawUser = raw;
    cachedUserSnapshot = JSON.parse(raw) as UserSummary;
    return cachedUserSnapshot;
  } catch {
    cachedRawUser = null;
    cachedUserSnapshot = null;
    return null;
  }
}

export function setStoredUser(user: UserSummary): void {
  cachedUserSnapshot = user;
  try {
    const serialized = JSON.stringify(user);
    cachedRawUser = serialized;
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(USER_STORAGE_KEY, serialized);
    }
  } catch {
    // Ignore localStorage write failures
  }
  notifySubscribers();
}

export const DEMO_CREDENTIALS = {
  administrator: { username: "admin", password: "AdminSecurePass!2026", role: "administrator" },
  doctor_reviewer: { username: "doctor", password: "DoctorSecurePass!2026", role: "doctor_reviewer" },
  researcher: { username: "researcher", password: "ResearcherPass!2026", role: "researcher" },
} as const;

export async function demoLogin(role: keyof typeof DEMO_CREDENTIALS): Promise<TokenResponse> {
  const creds = DEMO_CREDENTIALS[role];
  return login({ username: creds.username, password: creds.password });
}

export function getAuthHeader(): Record<string, string> {
  const token = getStoredToken();
  if (token && token.trim().length > 0) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

/**
 * Authenticate with the FastAPI backend using username/password.
 */
export async function login(payload: LoginPayload): Promise<TokenResponse> {
  const base = getApiBaseUrl();
  const url = `${base}/auth/login`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "Network error";
    throw new AuthApiError(`Failed to reach authentication service: ${msg}`, 0, "NETWORK_ERROR");
  }

  if (!response.ok) {
    let errorCode = `HTTP_${response.status}`;
    let errorMessage = "Authentication failed";
    try {
      const data = await response.json();
      if (data?.error?.message) {
        errorMessage = data.error.message;
        errorCode = data.error.code || errorCode;
      } else if (data?.detail) {
        errorMessage = data.detail;
      }
    } catch {
      // Non-json response
    }
    throw new AuthApiError(errorMessage, response.status, errorCode);
  }

  const tokenData = (await response.json()) as TokenResponse;
  cachedTokenSnapshot = tokenData.access_token;
  cachedRawToken = tokenData.access_token;
  cachedUserSnapshot = tokenData.user;
  try {
    const serialized = JSON.stringify(tokenData.user);
    cachedRawUser = serialized;
    if (typeof window !== "undefined" && window.localStorage) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, tokenData.access_token);
      window.localStorage.setItem(USER_STORAGE_KEY, serialized);
    }
  } catch {
    // Ignore storage write failure
  }
  notifySubscribers();
  return tokenData;
}

/**
 * Terminate active session and invalidate client credentials.
 */
export async function logout(): Promise<void> {
  const token = getStoredToken();
  if (token) {
    const base = getApiBaseUrl();
    const url = `${base}/auth/logout`;
    try {
      await fetch(url, {
        method: "POST",
        headers: {
          Accept: "application/json",
          ...getAuthHeader(),
        },
      });
    } catch {
      // Proceed with client-side cleanup regardless
    }
  }
  clearStoredToken();
}

/**
 * Fetch currently authenticated user from backend.
 */
export async function getCurrentUser(): Promise<UserSummary | null> {
  const token = getStoredToken();
  if (!token) return null;

  const base = getApiBaseUrl();
  const url = `${base}/auth/me`;

  try {
    const response = await fetch(url, {
      method: "GET",
      headers: {
        Accept: "application/json",
        ...getAuthHeader(),
      },
    });

    if (!response.ok) {
      if (response.status === 401) {
        clearStoredToken();
      }
      return null;
    }

    const user = (await response.json()) as UserSummary;
    setStoredUser(user);
    return user;
  } catch {
    return getStoredUser();
  }
}

function subscribeAuthStore(onStoreChange: () => void): () => void {
  storeSubscribers.add(onStoreChange);
  return () => {
    storeSubscribers.delete(onStoreChange);
  };
}

function getServerTokenSnapshot(): null {
  return null;
}

function getServerUserSnapshot(): null {
  return null;
}

/**
 * Reactive React hook returning the currently stored JWT access token.
 */
export function useAuthToken(): string | null {
  return useSyncExternalStore(
    subscribeAuthStore,
    getStoredToken,
    getServerTokenSnapshot
  );
}

/**
 * Reactive React hook returning the active authenticated UserSummary.
 */
export function useCurrentUser(): UserSummary | null {
  return useSyncExternalStore(
    subscribeAuthStore,
    getStoredUser,
    getServerUserSnapshot
  );
}
