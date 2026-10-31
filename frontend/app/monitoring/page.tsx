import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Deployment & Telemetry — Arogya AI",
  description: "Container orchestration health, service latency telemetry, database connection pools, and release runbooks.",
};

export default function MonitoringPage() {
  return (
    <PageContainer
      title="System Deployment, Telemetry &amp; Release Health"
      description="Container orchestration health (Docker Compose), API latency telemetry, runtime health probes, and release automation runbooks."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Deployment & Telemetry" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 20 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 20: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 20: Deployment, Monitoring & Release"
          targetBlock="Block 5: Platform Completion & Governance"
          statusText="Planned for a future module"
          description="Deployment, Monitoring & Release is scheduled for implementation in Module 20. It packages the monorepo into reproducible Docker Compose multi-container environments, sets up CI/CD test workflows, and connects Prometheus/Grafana telemetry. Container metrics collectors and live telemetry dashboards are not yet active in this frontend shell."
          verifiedFoundations={[
            "Backend Health Probes: `/health` and `/api/v1/health` endpoints (Module 2)",
            "Database Verification: `scripts/verify_database.py` connection check utility (Module 3)",
            "Environment Hardening: Zero-secrets-in-images policy and `.env.example` templates",
            "CI Test Gateways: Python pytest and Next.js static build automation (Module 1–4)",
          ]}
        />

        <section aria-labelledby="monitoring-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="monitoring-capabilities-heading" className={styles.sectionTitle}>
              Planned Telemetry &amp; Release Operations
            </h2>
            <p className={styles.sectionSubtitle}>
              Target deployment runbooks and observability pipelines defined in Module 20.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="2" width="20" height="8" rx="2" ry="2" />
                  <rect x="2" y="14" width="20" height="8" rx="2" ry="2" />
                  <line x1="6" y1="6" x2="6.01" y2="6" />
                  <line x1="6" y1="18" x2="6.01" y2="18" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Multi-Container Orchestration</h3>
              <p className={styles.pillarDescription}>
                Docker Compose stacks unifying FastAPI, PostgreSQL, Next.js frontend, and local
                object storage with health-check dependency sequencing.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>API Latency &amp; Error Metrics</h3>
              <p className={styles.pillarDescription}>
                Prometheus metrics tracking p95/p99 request latencies, HTTP 4xx/5xx error frequencies,
                and LangGraph agent execution durations.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Release Runbooks &amp; CI Gates</h3>
              <p className={styles.pillarDescription}>
                Automated continuous integration testing verifying clean-install rehearsals, zero uncommitted
                secrets, and migration reversibility prior to tagging releases.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
