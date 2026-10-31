import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Readiness & Model Cards — Arogya AI",
  description: "Academic research handover documentation, standardized model cards, and clinical safety gap analysis.",
};

export default function ReadinessPage() {
  return (
    <PageContainer
      title="Research Documentation &amp; Clinical Readiness Review"
      description="Academic handover documentation, standardized model cards, clinical safety gap analyses, and regulatory readiness checklists (MDR/FDA SaMD guidance)."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Readiness & Model Cards" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 21 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 21: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 21: Research Documentation & Readiness Review"
          targetBlock="Block 5: Platform Completion & Governance"
          statusText="Planned for a future module"
          description="Research Documentation & Readiness Review is the concluding milestone of the Arogya AI roadmap (Module 21). It compiles comprehensive academic handover packages, model documentation cards, and transparent catalogs of remaining clinical, privacy, and regulatory gaps. Handover documents and regulatory checklists are not yet finalized in this prototype shell."
          verifiedFoundations={[
            "Architecture Baseline: Complete 21-module dependency specification (MODULE_DEPENDENCIES.md)",
            "Research Prototype Notice: Prominent disclaimers across all application views and outputs",
            "Model Card Format: Standardized dataset, architecture, limitation, and fairness reporting templates",
            "Regulatory Gap Catalog: Explicit classification as research-only platform awaiting formal clinical trials",
          ]}
        />

        <section aria-labelledby="readiness-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="readiness-capabilities-heading" className={styles.sectionTitle}>
              Planned Readiness Deliverables
            </h2>
            <p className={styles.sectionSubtitle}>
              Final research handover and regulatory evaluation artifacts defined in Module 21.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
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
              <h3 className={styles.pillarTitle}>Standardized Model Cards</h3>
              <p className={styles.pillarDescription}>
                Formal specifications detailing training dataset demographics, baseline architectures,
                subgroup evaluation metrics, and verified operational failure modes.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Clinical Gap Analysis</h3>
              <p className={styles.pillarDescription}>
                Exhaustive, unvarnished inventory of clinical workflow, data distribution, and
                safety limitations requiring formal prospective trials prior to real-world translation.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                  <polyline points="22 4 12 14.01 9 11.01" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Regulatory Handover Package</h3>
              <p className={styles.pillarDescription}>
                Software-as-a-Medical-Device (SaMD) documentation alignment with EU MDR Annex II and
                FDA digital health pre-market evaluation recommendations.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
