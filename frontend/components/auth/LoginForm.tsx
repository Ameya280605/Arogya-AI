"use client";

import React, { useState } from "react";
import styles from "./LoginForm.module.css";
import {
  login,
  demoLogin,
  type UserSummary,
  type DEMO_CREDENTIALS,
} from "@/services/auth";

export interface LoginFormProps {
  title?: string;
  description?: string;
  redirectUrl?: string;
  onSuccess?: (user: UserSummary) => void;
  showQuickLogins?: boolean;
  className?: string;
}

export function LoginForm({
  title = "Sign In to Arogya AI",
  description = "Enter your clinical or research credentials to access protected healthcare workflows.",
  redirectUrl,
  onSuccess,
  showQuickLogins = true,
  className = "",
}: LoginFormProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSuccessfulAuth = (user: UserSummary) => {
    if (onSuccess) {
      onSuccess(user);
    }
    if (redirectUrl && typeof window !== "undefined") {
      window.location.assign(redirectUrl);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setErrorMessage("Please enter both username/email and password.");
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const res = await login({
        username: username.trim(),
        password,
      });
      handleSuccessfulAuth(res.user);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Authentication failed";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickLogin = async (role: keyof typeof DEMO_CREDENTIALS) => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await demoLogin(role);
      handleSuccessfulAuth(res.user);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Quick login failed";
      setErrorMessage(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className={`${styles.loginCard} ${className}`.trim()}>
      <div className={styles.loginHeader}>
        <div className={styles.iconContainer} aria-hidden="true">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
        </div>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.description}>{description}</p>
      </div>

      <form onSubmit={handleSubmit} className={styles.form}>
        {errorMessage && (
          <div className={styles.errorAlert} role="alert">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{errorMessage}</span>
          </div>
        )}

        <div className={styles.formGroup}>
          <label htmlFor="login-username" className={styles.label}>
            Username or Email
          </label>
          <input
            id="login-username"
            name="username"
            type="text"
            className={styles.input}
            placeholder="e.g. doctor or admin@arogya.local"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            disabled={isLoading}
            autoComplete="username"
            required
          />
        </div>

        <div className={styles.formGroup}>
          <label htmlFor="login-password" className={styles.label}>
            Password
          </label>
          <input
            id="login-password"
            name="password"
            type="password"
            className={styles.input}
            placeholder="••••••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            autoComplete="current-password"
            required
          />
        </div>

        <button
          type="submit"
          className={styles.submitButton}
          disabled={isLoading || !username.trim() || !password}
        >
          {isLoading ? "Verifying Credentials..." : "Sign In"}
        </button>
      </form>

      {showQuickLogins && (
        <div className={styles.quickSection}>
          <div className={styles.quickTitle}>Quick Role Presets (Synthetic Demo)</div>
          <div className={styles.quickGrid}>
            <button
              type="button"
              className={styles.quickButton}
              onClick={() => handleQuickLogin("doctor_reviewer")}
              disabled={isLoading}
            >
              <span>Doctor Reviewer (Clinician)</span>
              <span className={styles.quickRoleTag}>doctor_reviewer</span>
            </button>
            <button
              type="button"
              className={styles.quickButton}
              onClick={() => handleQuickLogin("administrator")}
              disabled={isLoading}
            >
              <span>System Administrator</span>
              <span className={styles.quickRoleTag}>administrator</span>
            </button>
            <button
              type="button"
              className={styles.quickButton}
              onClick={() => handleQuickLogin("researcher")}
              disabled={isLoading}
            >
              <span>Research Scientist</span>
              <span className={styles.quickRoleTag}>researcher</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
