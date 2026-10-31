import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Explainability & Evidence Presentation — Arogya AI",
  description: "Feature attribution waterfall plots (SHAP), visual saliency heatmaps (Grad-CAM), and evidence cross-referencing.",
};

export default function ExplainabilityPage() {
  return (
    <PageContainer
      title="Explainability &amp; Evidence Presentation (XAI)"
      description="Feature attribution (SHAP), visual saliency heatmaps (Grad-CAM), and guideline evidence cross-referencing to preserve clinical reasoning transparency."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Explainability & XAI" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 14 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 14: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 14: Explainability & Evidence Presentation"
          targetBlock="Block 3: AI Research & Multimodal Pipeline"
          statusText="Planned for a future module"
          description="Explainability & Evidence Presentation is scheduled for implementation in Module 14. It renders structured SHAP attribution charts for laboratory parameters, superimposes Grad-CAM heatmaps over radiographs, and links findings directly to medical literature. Interactive XAI visualizers and model attribution runners are not yet active in this frontend shell."
          verifiedFoundations={[
            "Relational Models: UploadedAsset and AnalysisRun schemas (Module 3)",
            "Scientific Integrity: Explicit distinction between statistical attribution and biological causation",
            "XAI Design: Reusable Card and Table primitives ready for waterfall charts and saliency overlays",
            "Literature Integration: Source-attributed citation schema models (Module 12 prerequisite)",
          ]}
        />

        <section aria-labelledby="xai-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="xai-capabilities-heading" className={styles.sectionTitle}>
              Planned XAI Capabilities
            </h2>
            <p className={styles.sectionSubtitle}>
              Transparency and evidence attribution visualizers planned in Module 14.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="20" x2="18" y2="10" />
                  <line x1="12" y1="20" x2="12" y2="4" />
                  <line x1="6" y1="20" x2="6" y2="14" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>SHAP Feature Attribution</h3>
              <p className={styles.pillarDescription}>
                Waterfall and summary plots showing the exact mathematical contribution of individual
                vitals and laboratory panels toward the baseline tabular risk score.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Grad-CAM Saliency Overlays</h3>
              <p className={styles.pillarDescription}>
                High-resolution heatmaps highlighting localized lung zones driving vision model
                activations, toggleable directly over DICOM chest radiographs.
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
              <h3 className={styles.pillarTitle}>Evidence Synthesis Matrix</h3>
              <p className={styles.pillarDescription}>
                Side-by-side presentation aligning observational findings with corresponding guideline
                passages, confidence intervals, and clinician review prompts.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
