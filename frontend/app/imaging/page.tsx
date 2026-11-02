import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { ImagingWorkspace } from "@/components/imaging/ImagingWorkspace";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Chest X-ray Imaging Research — Arogya AI",
  description: "Research-only chest X-ray inference for uploaded PNG/JPEG images with optional Grad-CAM heatmaps.",
};

export default function ImagingPage() {
  return (
    <PageContainer
      title="Chest X-ray Imaging &amp; Research Pipeline"
      description="Run research-only inference on uploaded PNG/JPEG chest X-rays and optionally review Grad-CAM heatmaps."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Chest X-ray Research" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Module 10 imaging research workflow"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 10: Research workflow</span>
        </div>
      }
    >
      <ImagingWorkspace />
    </PageContainer>
  );
}
