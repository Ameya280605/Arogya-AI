"use client";

import React, { useState, useEffect } from "react";
import styles from "./SecurityConsole.module.css";
import {
  login,
  logout,
  getCurrentUser,
  getStoredToken,
  onAuthChange,
  type UserSummary,
} from "@/services/auth";

interface UploadResult {
  id: string;
  original_filename: string;
  media_type: string;
  file_size_bytes: number;
  checksum_sha256: string;
}

export function SecurityConsole() {
  const [currentUser, setCurrentUser] = useState<UserSummary | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authMessage, setAuthMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // File Upload State
  const [patientId, setPatientId] = useState("");
  const [encounterId, setEncounterId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    getCurrentUser()
      .then((user) => {
        if (isMounted && user) {
          setCurrentUser(user);
          setToken(getStoredToken());
        }
      })
      .catch(() => {
        if (isMounted) {
          setCurrentUser(null);
        }
      });

    const unsub = onAuthChange((newUser) => {
      if (isMounted) {
        setCurrentUser(newUser);
        setToken(getStoredToken());
      }
    });

    return () => {
      isMounted = false;
      unsub();
    };
  }, []);

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setAuthLoading(true);
    setAuthMessage(null);
    try {
      const res = await login({ username, password });
      setCurrentUser(res.user);
      setToken(res.access_token);
      setAuthMessage({ type: "success", text: `Authenticated as ${res.user.role} (${res.user.email})` });
      setPassword("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setAuthMessage({ type: "error", text: msg });
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = async () => {
    setAuthLoading(true);
    try {
      await logout();
      setCurrentUser(null);
      setToken(null);
      setAuthMessage({ type: "success", text: "Logged out successfully" });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Logout failed";
      setAuthMessage({ type: "error", text: msg });
    } finally {
      setAuthLoading(false);
    }
  };

  const handleQuickLogin = async (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setAuthLoading(true);
    setAuthMessage(null);
    try {
      const res = await login({ username: user, password: pass });
      setCurrentUser(res.user);
      setToken(res.access_token);
      setAuthMessage({ type: "success", text: `Authenticated as ${res.user.role} (${res.user.email})` });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Login failed";
      setAuthMessage({ type: "error", text: msg });
    } finally {
      setAuthLoading(false);
    }
  };

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setUploadError("Please select a file to upload");
      return;
    }
    if (!patientId.trim()) {
      setUploadError("Patient UUID is required");
      return;
    }

    setUploadLoading(true);
    setUploadError(null);
    setUploadResult(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("patient_id", patientId.trim());
      if (encounterId.trim()) {
        formData.append("encounter_id", encounterId.trim());
      }

      const activeToken = getStoredToken();
      const headers: Record<string, string> = {
        Accept: "application/json",
      };
      if (activeToken) {
        headers["Authorization"] = `Bearer ${activeToken}`;
      }

      const res = await fetch("http://127.0.0.1:8000/api/v1/assets/upload", {
        method: "POST",
        headers,
        body: formData,
      });

      const data = (await res.json()) as UploadResult & {
        error?: { message?: string };
        detail?: string;
      };
      if (!res.ok) {
        throw new Error(data?.error?.message || data?.detail || `Upload failed with status ${res.status}`);
      }

      setUploadResult({
        id: data.id,
        original_filename: data.original_filename,
        media_type: data.media_type,
        file_size_bytes: data.file_size_bytes,
        checksum_sha256: data.checksum_sha256,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to upload asset";
      setUploadError(msg);
    } finally {
      setUploadLoading(false);
    }
  };

  const getRoleBadgeClass = (role?: string) => {
    switch (role) {
      case "administrator":
        return styles.badgeAdmin;
      case "doctor_reviewer":
      case "clinician":
        return styles.badgeDoctor;
      case "researcher":
        return styles.badgeResearcher;
      default:
        return styles.badgeGuest;
    }
  };

  return (
    <div className={styles.consoleContainer}>
      {/* Auth & Identity Management */}
      <section className={styles.card} aria-labelledby="auth-controls-heading">
        <div className={styles.cardHeader}>
          <h3 id="auth-controls-heading" className={styles.cardTitle}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
            Identity &amp; Session Management
          </h3>
          <span className={`${styles.badge} ${getRoleBadgeClass(currentUser?.role)}`}>
            {currentUser ? `Role: ${currentUser.role}` : "Unauthenticated"}
          </span>
        </div>

        {currentUser ? (
          <div>
            <p>
              Active user: <strong>{currentUser.email}</strong> (ID: <code>{currentUser.id}</code>)
            </p>
            {token && (
              <p style={{ marginTop: 8, fontSize: "0.8rem", color: "#64748b" }}>
                Active JWT Bearer Token: <code>{token.slice(0, 16)}...{token.slice(-10)}</code>
              </p>
            )}
            <div className={styles.buttonGroup} style={{ marginTop: 16 }}>
              <button
                type="button"
                className={styles.dangerButton}
                onClick={handleLogout}
                disabled={authLoading}
              >
                {authLoading ? "Logging out..." : "Sign Out"}
              </button>
            </div>
          </div>
        ) : (
          <div>
            <form onSubmit={handleLogin} className={styles.formGrid}>
              <div className={styles.formGroup}>
                <label htmlFor="auth-username" className={styles.label}>
                  Username or Email
                </label>
                <input
                  id="auth-username"
                  type="text"
                  className={styles.input}
                  placeholder="admin or user@arogya.ai"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />
              </div>

              <div className={styles.formGroup}>
                <label htmlFor="auth-password" className={styles.label}>
                  Password
                </label>
                <input
                  id="auth-password"
                  type="password"
                  className={styles.input}
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </form>

            <div className={styles.buttonGroup}>
              <button
                type="button"
                className={styles.primaryButton}
                onClick={() => handleLogin()}
                disabled={authLoading || !username || !password}
              >
                {authLoading ? "Signing In..." : "Sign In"}
              </button>

              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => handleQuickLogin("doctor", "DoctorSecurePass!2026")}
                disabled={authLoading}
              >
                Quick Doctor Login
              </button>

              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => handleQuickLogin("admin", "AdminSecurePass!2026")}
                disabled={authLoading}
              >
                Quick Admin Login
              </button>

              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => handleQuickLogin("researcher", "ResearcherPass!2026")}
                disabled={authLoading}
              >
                Quick Researcher Login
              </button>
            </div>
          </div>
        )}

        {authMessage && (
          <div
            className={`${styles.alertBox} ${
              authMessage.type === "success" ? styles.alertSuccess : styles.alertError
            }`}
            role="status"
          >
            {authMessage.text}
          </div>
        )}
      </section>

      {/* Asset Intake & Security Verification */}
      <div className={styles.gridTwoCol}>
        <section className={styles.card} aria-labelledby="asset-upload-heading">
          <div className={styles.cardHeader}>
            <h3 id="asset-upload-heading" className={styles.cardTitle}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              Clinical Asset Ingestion &amp; Verification
            </h3>
          </div>

          <form onSubmit={handleFileUpload}>
            <div className={styles.formGroup} style={{ marginBottom: 12 }}>
              <label htmlFor="asset-patient-id" className={styles.label}>
                Patient UUID
              </label>
              <input
                id="asset-patient-id"
                type="text"
                className={styles.input}
                placeholder="e.g. 00000000-0000-0000-0000-000000000001"
                value={patientId}
                onChange={(e) => setPatientId(e.target.value)}
                required
              />
            </div>

            <div className={styles.formGroup} style={{ marginBottom: 12 }}>
              <label htmlFor="asset-encounter-id" className={styles.label}>
                Encounter UUID (Optional)
              </label>
              <input
                id="asset-encounter-id"
                type="text"
                className={styles.input}
                placeholder="Optional encounter association"
                value={encounterId}
                onChange={(e) => setEncounterId(e.target.value)}
              />
            </div>

            <div className={styles.formGroup} style={{ marginBottom: 16 }}>
              <label htmlFor="asset-file" className={styles.label}>
                Select Radiograph / Report (PNG, JPEG, PDF, DICOM)
              </label>
              <input
                id="asset-file"
                type="file"
                accept=".png,.jpg,.jpeg,.pdf,.dcm,image/png,image/jpeg,application/pdf,application/dicom"
                className={styles.input}
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                required
              />
            </div>

            <button
              type="submit"
              className={styles.primaryButton}
              disabled={uploadLoading || !selectedFile}
            >
              {uploadLoading ? "Validating & Uploading..." : "Upload & Inspect File"}
            </button>
          </form>

          {uploadError && (
            <div className={`${styles.alertBox} ${styles.alertError}`} role="alert">
              <strong>Error:</strong> {uploadError}
            </div>
          )}

          {uploadResult && (
            <div className={`${styles.alertBox} ${styles.alertSuccess}`} role="status">
              <div><strong>Asset Stored Safely:</strong></div>
              <div>ID: <code>{uploadResult.id}</code></div>
              <div>Filename: <code>{uploadResult.original_filename}</code></div>
              <div>MIME: <code>{uploadResult.media_type}</code></div>
              <div>Size: <code>{uploadResult.file_size_bytes} bytes</code></div>
              <div>SHA-256: <code>{uploadResult.checksum_sha256}</code></div>
              <div style={{ marginTop: 8 }}>
                <a
                  href={`http://127.0.0.1:8000/api/v1/assets/${uploadResult.id}/download`}
                  target="_blank"
                  rel="noreferrer"
                  className={styles.secondaryButton}
                  style={{ display: "inline-block", textDecoration: "none" }}
                >
                  Download Binary (Authenticated)
                </a>
              </div>
            </div>
          )}
        </section>

        {/* Security Safeguards Overview */}
        <section className={styles.card} aria-labelledby="safeguards-heading">
          <div className={styles.cardHeader}>
            <h3 id="safeguards-heading" className={styles.cardTitle}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                <path d="M7 11V7a5 5 0 0 1 10 0v4" />
              </svg>
              Enforced Security Controls
            </h3>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <strong>Least-Privilege Roles &amp; Permissions:</strong>
              <div className={styles.permissionTagList}>
                <span className={styles.permissionTag}>administrator</span>
                <span className={styles.permissionTag}>doctor_reviewer</span>
                <span className={styles.permissionTag}>researcher</span>
              </div>
            </div>

            <div>
              <strong>Safe Storage Architecture:</strong>
              <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "4px 0" }}>
                Files are written outside web roots to <code>storage/uploads/</code> using server-generated UUIDs. Raw client paths are sanitized against traversal attacks.
              </p>
            </div>

            <div>
              <strong>Cryptographic Integrity &amp; Audit Trail:</strong>
              <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "4px 0" }}>
                Each uploaded asset generates a SHA-256 checksum. All auth actions, file operations, and access denials append to the immutable <code>AuditEvent</code> ledger with credential scrubbing.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
