import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import { SecurityConsole } from "@/components/security/SecurityConsole";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Security, Identity & File Handling — Arogya AI",
  description: "Role-based access boundaries, session security, cryptographic audit verification, and validated medical file intake.",
};

export default function SecurityPage() {
  return (
    <PageContainer
      title="Security, Identity &amp; Data Safeguards"
      description="Role-based access boundaries (RBAC), multi-factor session validation, cryptographic audit event tracking, and validated medical asset handling."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Security & Safeguards" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 7 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 7: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 7: Security, Identity & File Handling"
          targetBlock="Block 2: Core Workflows"
          statusText="Planned for a future module"
          description="Security, Identity & File Handling is scheduled for implementation in Module 7. It establishes cross-patient access controls, cryptographic session token verification, and strict MIME/magic-byte image upload validation. Interactive login dialogs, live permission evaluation, and file storage APIs are not yet active in this frontend shell."
          verifiedFoundations={[
            "Relational Models: User, UserRole, AuditEvent (Module 3)",
            "Asset Metadata: UploadedAsset schema with SHA-256 integrity hashes",
            "Pydantic Contracts: UserResponse, AuditEventResponse, AssetMetadata",
            "Security Boundaries: Target architecture trust boundary specifications",
          ]}
        />

        <SecurityConsole />

        <section aria-labelledby="security-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="security-capabilities-heading" className={styles.sectionTitle}>
              Planned Security Safeguards
            </h2>
            <p className={styles.sectionSubtitle}>
              Core identity, asset intake, and authorization capabilities defined for Module 7.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                  <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Role-Based Access Control (RBAC)</h3>
              <p className={styles.pillarDescription}>
                Granular permission boundaries strictly separating Clinicians, Clinical Reviewers,
                Research Scientists, and System Administrators.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                  <polyline points="17 8 12 3 7 8" />
                  <line x1="12" y1="3" x2="12" y2="15" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Secure Asset Ingestion</h3>
              <p className={styles.pillarDescription}>
                Strict magic-byte header inspection, decompression bomb mitigation, and quarantine
                pipelines for de-identified DICOM and PNG radiograph uploads.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Cryptographic Audit Verification</h3>
              <p className={styles.pillarDescription}>
                Append-only audit trail logging user authentication events, asset access attempts,
                and administrative role modifications.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
