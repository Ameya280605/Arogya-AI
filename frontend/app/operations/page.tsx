import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Hospital Intelligence & Operations — Arogya AI",
  description: "Operational throughput metrics, bed capacity simulation, and inference compute/storage cost modeling.",
};

export default function OperationsPage() {
  return (
    <PageContainer
      title="Hospital Intelligence &amp; Resource Simulation"
      description="Departmental workload trends, bed capacity simulation, and transparent compute inference / storage cost modeling."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Hospital Intelligence" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 17 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 17: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 17: Hospital Intelligence & Financial Analytics"
          targetBlock="Block 5: Platform Completion & Governance"
          statusText="Planned for a future module"
          description="Hospital Intelligence & Financial Analytics is scheduled for implementation in Module 17. It models department throughput, simulates resource demands, and estimates inference hardware and storage expenses. Live hospital administrative connectors and cost simulation engines are not yet active in this frontend shell."
          verifiedFoundations={[
            "Data Segregation: Strict architectural separation of measured data from projected scenario estimates",
            "Relational Baseline: Encounter and patient counts from Module 3 development seed data",
            "Cost Transparency: Explicit formula parameters for GPU token inference and DICOM storage pricing",
            "Platform Alignment: Feeds into platform administration and monitoring (Modules 19 & 20)",
          ]}
        />

        <section aria-labelledby="operations-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="operations-capabilities-heading" className={styles.sectionTitle}>
              Planned Operational Analytics
            </h2>
            <p className={styles.sectionSubtitle}>
              Core operational metrics and financial resource modeling defined in Module 17.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M3 3v18h18" />
                  <path d="m19 9-5 5-4-4-3 3" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Departmental Throughput</h3>
              <p className={styles.pillarDescription}>
                Aggregated synthetic statistics on patient admission rates, encounter duration, and
                clinical specialty consultation bottlenecks.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Bed &amp; Resource Capacity</h3>
              <p className={styles.pillarDescription}>
                Scenario modeling tracking intensive care unit (ICU) and general medical bed utilization
                against projected seasonal respiratory surges.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="12" y1="1" x2="12" y2="23" />
                  <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Inference &amp; Storage Cost Models</h3>
              <p className={styles.pillarDescription}>
                Transparent breakdown projecting cloud compute costs per analysis run, GPU inference hours,
                and long-term encrypted object storage for radiology archives.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
