import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Clinical Workspace — Arogya AI",
  description: "Multimodal clinical case intake, investigation workflows, and inference runners.",
};

export default function AnalysisPage() {
  return (
    <PageContainer
      title="Clinical Workspace &amp; Case Analysis"
      description="Multimodal case intake, diagnostic assistance, observation panels, and evidence synthesis workflows."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Clinical Workspace" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 8 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 8: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        {/* Module Implementation Status Callout using PlannedFeatureState */}
        <PlannedFeatureState
          moduleName="Module 8: Clinical Workspace & Case Analysis"
          targetBlock="Block 2: Clinical Domain Foundation"
          statusText="Planned for a future module"
          description="The Clinical Workspace is scheduled for implementation in Module 8. It brings together patient context (Module 6), secure file handling (Module 7), and AI inference pipelines (Modules 9–14). Multimodal case runners and live clinical inference pipelines are not yet connected to this frontend shell."
          verifiedFoundations={[
            "Persistence Entities: AnalysisRun, UploadedAsset (Module 3)",
            "Execution Lifecycle: QUEUED, RUNNING, COMPLETED, FAILED states",
            "Audit Integration: AuditEvent linked to analysis run IDs",
            "Inference Architecture: Scikit-Learn Tabular (M9) + PyTorch Vision (M10)",
          ]}
        />

        {/* Planned Architecture Specifications */}
        <section aria-labelledby="analysis-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="analysis-capabilities-heading" className={styles.sectionTitle}>
              Planned Workspace Workflows
            </h2>
            <p className={styles.sectionSubtitle}>
              Interactive clinician tools planned across the core roadmap.
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
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Case Intake &amp; Triage</h3>
              <p className={styles.pillarDescription}>
                Structured entry for chief complaint, history of present illness, vital signs,
                and preliminary laboratory observations.
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
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Medical Imaging Attachment</h3>
              <p className={styles.pillarDescription}>
                De-identified DICOM and Chest X-ray uploads with cryptographic hash verification
                and metadata validation.
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
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Clinician Critique &amp; Review</h3>
              <p className={styles.pillarDescription}>
                Structured approval, refinement, or rejection controls where healthcare
                professionals retain authority over every clinical finding.
              </p>
            </article>
          </div>
        </section>

        {/* Analysis Run Model Status */}
        <section className={styles.specCard} aria-labelledby="analysis-model-heading">
          <div className={styles.specHeader}>
            <div>
              <h2 id="analysis-model-heading" className={styles.sectionTitle}>
                Data Pipeline Alignment
              </h2>
              <p className={styles.sectionSubtitle}>
                Relational run contracts established in Module 3.
              </p>
            </div>
            <div className={styles.statusTags}>
              <span className={styles.badgeSuccess}>Entities Pinned</span>
              <span className={styles.badgeInfo}>Module 3 Verified</span>
            </div>
          </div>

          <div className={styles.specGrid}>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Persistence Entity</span>
              <span className={styles.specValue}>AnalysisRun, UploadedAsset</span>
            </div>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Execution State</span>
              <span className={styles.specValue}>QUEUED, RUNNING, COMPLETED, FAILED</span>
            </div>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Audit Association</span>
              <span className={styles.specValue}>AuditEvent linked to run IDs</span>
            </div>
            <div className={styles.specItem}>
              <span className={styles.specLabel}>Inference Engines</span>
              <span className={styles.specValue}>Tabular (M9) + Vision (M10)</span>
            </div>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
