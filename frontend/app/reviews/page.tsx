import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Doctor Review & Feedback — Arogya AI",
  description: "Clinician oversight interface: structured findings review, override controls, and audit preservation.",
};

export default function ReviewsPage() {
  return (
    <PageContainer
      title="Clinician Review, Critique &amp; Structured Reporting"
      description="Clinician oversight workstation: review, accept, modify, or reject AI-assisted findings with immutable audit trails separating model output from doctor edits."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Doctor Review & Reports" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 15 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 15: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 15: Reports, Doctor Review & Feedback"
          targetBlock="Block 4: Human Workflow & Care"
          statusText="Planned for a future module"
          description="Reports, Doctor Review & Feedback is scheduled for implementation in Module 15. It provides the central human-in-the-loop workstation where medical professionals exercise sovereign clinical authority over AI-assisted observations before reports are finalized. Interactive review workflows, structured sign-offs, and report export engines are not yet active in this frontend shell."
          verifiedFoundations={[
            "Data Contracts: AuditEvent schema tracking clinician overrides (Module 3)",
            "Provenance Separation: Relational design isolating raw AI findings from clinician edits",
            "Human Sovereignty: Core principle that AI outputs remain research artifacts until signed off",
            "Report Schemas: Structured summary contracts connecting to patient timelines (Module 16)",
          ]}
        />

        <section aria-labelledby="reviews-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="reviews-capabilities-heading" className={styles.sectionTitle}>
              Planned Review Workflows
            </h2>
            <p className={styles.sectionSubtitle}>
              Core clinical review, editing, and report finalization controls planned for Module 15.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Accept, Modify or Reject</h3>
              <p className={styles.pillarDescription}>
                Granular controls allowing clinicians to endorse valid signals, refine diagnostic
                language, or reject unverified AI outputs with required rationale notes.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Structured Report Generator</h3>
              <p className={styles.pillarDescription}>
                Exportable clinical evaluation reports containing chief complaints, verified vitals,
                radiographic interpretations, and doctor sign-off metadata.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Override Audit Trail</h3>
              <p className={styles.pillarDescription}>
                Immutable record logging the exact delta between raw model inferences and final
                clinician revisions for clinical governance and algorithmic refinement.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
