import type { Metadata } from "next";
import { Suspense } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { LoginForm } from "@/components/auth/LoginForm";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Sign In — Arogya AI",
  description: "Role-based authentication and clinical session verification for Arogya AI.",
};

export default function LoginPage() {
  return (
    <PageContainer
      title="Secure Identity &amp; Access"
      description="Authenticate with clinical or administrative clearance to access patient records, longitudinal trajectories, and medical asset ingestion."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Sign In" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Module 7 Security Active"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 7: Security Active</span>
        </div>
      }
    >
      <div className={styles.container}>
        {/* Research & Governance Safety Banner */}
        <section
          className={styles.disclaimerBox}
          aria-labelledby="login-safety-heading"
        >
          <div className={styles.disclaimerIcon} aria-hidden="true">
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
          <div className={styles.disclaimerBody}>
            <h2 id="login-safety-heading" className={styles.disclaimerTitle}>
              Clinical Identity &amp; Session Guard
            </h2>
            <p className={styles.disclaimerText}>
              All access to clinical cohorts, longitudinal profiles, and diagnostic asset pipelines is access-controlled
              under strict role-based permission boundaries (RBAC). Passwords are never stored in plaintext, and session tokens
              are cryptographically signed and audited.
            </p>
          </div>
        </section>

        <Suspense fallback={<div>Loading authentication console...</div>}>
          <LoginForm redirectUrl="/patients" />
        </Suspense>
      </div>
    </PageContainer>
  );
}
