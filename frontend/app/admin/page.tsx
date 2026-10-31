import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState, AccessDeniedState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Administration & Governance — Arogya AI",
  description: "Platform governance, immutable audit logs, role-based access control, and environment configuration.",
};

export default function AdminPage() {
  return (
    <PageContainer
      title="Administration &amp; Governance"
      description="Role-based access control (RBAC), immutable audit logging, model version registry, and runtime platform configuration."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Administration" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 19 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 19: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        {/* Module Implementation Status Callout using PlannedFeatureState */}
        <PlannedFeatureState
          moduleName="Module 19: Platform Administration & Governance"
          targetBlock="Block 5: Production Readiness & Verification"
          statusText="Planned for a future module"
          description="Platform Administration & Governance is scheduled for implementation in Module 19. The underlying database schema for users, roles, and immutable audit events was established and verified in Module 3. Live administration dashboards, user management forms, and interactive audit log explorers are not yet connected to this frontend shell."
          verifiedFoundations={[
            "Database Schema: User, UserRole, AuditEvent models (Module 3)",
            "Audit Integrity: Cryptographic append-only immutable event logs",
            "Repositories: AuditEventRepository & User domain services",
            "Pydantic Schemas: AuditEventCreate, AuditEventResponse",
          ]}
        />

        {/* Planned Architecture Specifications */}
        <section aria-labelledby="admin-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="admin-capabilities-heading" className={styles.sectionTitle}>
              Planned Governance Controls
            </h2>
            <p className={styles.sectionSubtitle}>
              Target compliance and administrative features planned in Block 5.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Immutable Audit Trail</h3>
              <p className={styles.pillarDescription}>
                Cryptographically verifiable, append-only audit event records capturing case
                creation, model inferences, clinician overrides, and system configuration changes.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="8.5" cy="7" r="4" />
                  <line x1="20" y1="8" x2="20" y2="14" />
                  <line x1="23" y1="11" x2="17" y2="11" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Role-Based Access Control (RBAC)</h3>
              <p className={styles.pillarDescription}>
                Explicit segregation of duties enforcing distinct permission boundaries between
                Physicians, Clinical Reviewers, Research Scientists, and System Administrators.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg
                  width="22"
                  height="22"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="12" cy="12" r="3" />
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Runtime Hardening</h3>
              <p className={styles.pillarDescription}>
                Environment variable verification, rate-limiting parameter tuning, secret-free
                logging configurations, and database connection pool monitoring.
              </p>
            </article>
          </div>
        </section>

        {/* Audit Readiness Specification */}
        <section className={styles.specCard} aria-labelledby="admin-backend-heading">
          <div className={styles.specHeader}>
            <div>
              <h2 id="admin-backend-heading" className={styles.sectionTitle}>
                Audit Schema Readiness
              </h2>
              <p className={styles.sectionSubtitle}>
                Persistence layer status verified in Module 3.
              </p>
            </div>
            <div className={styles.statusTags}>
              <span className={styles.badgeSuccess}>Audit Tables Active</span>
              <span className={styles.badgeInfo}>Module 3 Verified</span>
            </div>
          </div>

          <div className={styles.specGrid}>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Database Model</span>
              <span className={styles.specValue}>User, UserRole, AuditEvent</span>
            </div>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Audit Retention</span>
              <span className={styles.specValue}>Append-only immutable event logs</span>
            </div>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Repository</span>
              <span className={styles.specValue}>AuditEventRepository</span>
            </div>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Pydantic Contracts</span>
              <span className={styles.specValue}>AuditEventCreate, AuditEventResponse</span>
            </div>
          </div>
        </section>

        {/* Access-Denied Presentation Demonstration */}
        <section aria-labelledby="admin-access-demo-heading">
          <div className={styles.sectionHeading}>
            <h2 id="admin-access-demo-heading" className={styles.sectionTitle}>
              Access Boundary Presentation Pattern
            </h2>
            <p className={styles.sectionSubtitle}>
              Reusable UI state rendered when a session lacks the administrative governance role.
            </p>
          </div>

          <AccessDeniedState
            title="Administrative Access Restricted"
            message="This area requires system governance privileges. Physician and Research Scientist sessions are restricted from altering audit configuration or database connection pools."
            requiredRole="Platform Administrator"
          />
        </section>
      </div>
    </PageContainer>
  );
}
