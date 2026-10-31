import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Medical Knowledge Hub & RAG — Arogya AI",
  description: "Curated clinical practice guidelines, vector embeddings, source-attributed RAG, and prompt-injection defenses.",
};

export default function KnowledgePage() {
  return (
    <PageContainer
      title="Medical Knowledge Hub &amp; Guideline Retrieval"
      description="Curated clinical guideline indexing, vector embeddings, source-attributed retrieval-augmented generation (RAG), and prompt-injection defenses."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Medical Knowledge Hub" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 12 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 12: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 12: Medical Knowledge Hub & RAG"
          targetBlock="Block 3: AI Research & Multimodal Pipeline"
          statusText="Planned for a future module"
          description="The Medical Knowledge Hub & RAG is scheduled for implementation in Module 12. It establishes vector search over peer-reviewed medical practice guidelines, strict provenance citations, and defenses against untrusted document injections. Live vector search indexes and retrieval services are not yet connected to this frontend shell."
          verifiedFoundations={[
            "Data Contracts: Source citation metadata schema models (Module 3)",
            "Trust Boundaries: External medical literature classified as untrusted input (Arch Spec)",
            "Retrieval Criteria: Strict minimum cosine similarity thresholding to avoid hallucinated citations",
            "Knowledge Baseline: Curated public clinical guidelines index architecture (M12)",
          ]}
        />

        <section aria-labelledby="knowledge-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="knowledge-capabilities-heading" className={styles.sectionTitle}>
              Planned Knowledge Retrieval Capabilities
            </h2>
            <p className={styles.sectionSubtitle}>
              Target guideline ingestion and evidence attribution mechanisms defined for Module 12.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                  <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Curated Clinical Guidelines Index</h3>
              <p className={styles.pillarDescription}>
                Vector embeddings of verified clinical guidelines (e.g., ACC/AHA, GOLD, KDIGO)
                chunked with semantic boundary preservation.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Source Citation &amp; Provenance</h3>
              <p className={styles.pillarDescription}>
                Every retrieved passage links directly to published guideline sections, publication
                year, and evidentiary grade to eliminate unsourced claims.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Prompt-Injection Mitigation</h3>
              <p className={styles.pillarDescription}>
                Sanitization and structural isolation of retrieved text blocks to prevent prompt hijacking
                or malicious instruction overrides from external documents.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
