import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Chest X-ray Imaging Research — Arogya AI",
  description: "Chest radiography preprocessing, deep learning vision models, DICOM viewers, and Grad-CAM saliency heatmaps.",
};

export default function ImagingPage() {
  return (
    <PageContainer
      title="Chest X-ray Imaging &amp; Research Pipeline"
      description="Chest radiography preprocessing, deep learning vision inference, DICOM inspection, and Grad-CAM saliency heatmap generation."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Chest X-ray Research" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 10 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 10: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 10: Chest X-ray Imaging Research"
          targetBlock="Block 3: AI Research & Multimodal Pipeline"
          statusText="Planned for a future module"
          description="Chest X-ray Imaging Research is scheduled for implementation in Module 10. It establishes medical image normalization, PyTorch deep learning vision models for thoracic finding detection, and Grad-CAM saliency map generation. Live DICOM rendering and deep learning image inference pipelines are not yet active in this frontend shell."
          verifiedFoundations={[
            "Relational Models: UploadedAsset entity with MIME/format metadata (Module 3)",
            "Execution State: AnalysisRun linkage to imaging asset IDs (Module 3)",
            "Safety Bounds: Automated rejection of corrupted or non-medical images",
            "Pipeline Architecture: PyTorch torchvision integration specification (M10)",
          ]}
        />

        <section aria-labelledby="imaging-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="imaging-capabilities-heading" className={styles.sectionTitle}>
              Planned Vision Capabilities
            </h2>
            <p className={styles.sectionSubtitle}>
              Core imaging analysis and visual explainability features designed for Module 10.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>DICOM &amp; Radiograph Preprocessing</h3>
              <p className={styles.pillarDescription}>
                Standardized histogram equalization, contrast-limited adaptive CLAHE, and orientation
                normalization for anterior-posterior (AP) and posterior-anterior (PA) chest views.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Deep Learning Vision Pipeline</h3>
              <p className={styles.pillarDescription}>
                Multi-label thoracic finding screening using calibrated convolutional or vision
                transformer backbones trained exclusively on de-identified benchmarks.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="16" x2="12" y2="12" />
                  <line x1="12" y1="8" x2="12.01" y2="8" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Grad-CAM Saliency Maps</h3>
              <p className={styles.pillarDescription}>
                Visual gradient-weighted class activation mapping superimposed on radiographs to highlight
                anatomical regions driving model feature activations.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
