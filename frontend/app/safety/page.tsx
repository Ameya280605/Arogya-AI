import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Critic, Consensus & Safety — Arogya AI",
  description: "Cross-agent contradiction detection, clinical disagreement preservation, uncertainty estimation, and abstention triggers.",
};

export default function SafetyPage() {
  return (
    <PageContainer
      title="Critic, Consensus &amp; Calibrated Safety"
      description="Contradiction checking across multimodal findings, clinical disagreement preservation, entropy-based uncertainty calibration, and safety abstention triggers."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Critic & Safety" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 13 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 13: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 13: Critic, Consensus, Uncertainty & Safety"
          targetBlock="Block 3: AI Research & Multimodal Pipeline"
          statusText="Planned for a future module"
          description="The Critic, Consensus, Uncertainty & Safety system is scheduled for implementation in Module 13. It inspects multimodal outputs for contradictory evidence, prevents artificial consensus when models disagree, and triggers automatic abstention when confidence is uncalibrated. Safety rule engines and contradiction detectors are not yet active in this frontend shell."
          verifiedFoundations={[
            "Data Contracts: AnalysisRun state transitions and failure flags (Module 3)",
            "Safety Architecture: Disagreement preservation principle over forced consensus (Arch Spec)",
            "Abstention Triggering: Low-evidence thresholding protocol specifications",
            "Multi-Agent Gate: Prerequisite for clinician review and reporting in Module 15",
          ]}
        />

        <section aria-labelledby="safety-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="safety-capabilities-heading" className={styles.sectionTitle}>
              Planned Clinical Safety Mechanisms
            </h2>
            <p className={styles.sectionSubtitle}>
              Core algorithmic safety controls and uncertainty safeguards designed for Module 13.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Contradiction Detection</h3>
              <p className={styles.pillarDescription}>
                Automated rule checking that flags discrepancies between structured laboratory
                observations and natural language inference summaries.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Preserved Disagreement</h3>
              <p className={styles.pillarDescription}>
                When specialized sub-agents arrive at conflicting assessments, disagreement is explicitly
                preserved in the clinical report rather than smoothed over with majority voting.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M18.36 6.64a9 9 0 1 1-12.73 0" />
                  <line x1="12" y1="2" x2="12" y2="12" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Calibrated Abstention</h3>
              <p className={styles.pillarDescription}>
                When model predictive entropy exceeds safety bounds or required physiological inputs
                are absent, the system explicitly abstains from generating assistive suggestions.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
