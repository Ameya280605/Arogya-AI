import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { ClinicalWorkspace } from "@/components/clinical/ClinicalWorkspace";

export const metadata: Metadata = {
  title: "Clinical Workspace — Arogya AI",
  description: "Patient-scoped case intake, clinical data quality, secure attachments, and research analysis.",
};

export default function AnalysisPage() {
  return (
    <PageContainer
      title="Clinical Workspace"
      description="Create and review patient-linked clinical cases, measurements, attachments, and research runs."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Clinical Workspace" },
      ]}
      badge={<span role="status">Module 8 · Clinical workflow</span>}
    >
      <ClinicalWorkspace />
    </PageContainer>
  );
}
