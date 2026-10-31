import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Patient Timeline & Follow-up — Arogya AI",
  description: "Longitudinal encounter trajectories, physiological trend charts, and staff follow-up coordination.",
};

export default function TimelinePage() {
  return (
    <PageContainer
      title="Longitudinal Patient Trajectory &amp; Follow-up"
      description="Longitudinal encounter timelines, physiological trend tracking, ambulatory care trajectories, and staff-only follow-up task coordination."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Care Trajectory & Follow-up" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 16 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 16: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 16: Patient Timeline & Follow-up"
          targetBlock="Block 4: Human Workflow & Care"
          statusText="Planned for a future module"
          description="Patient Timeline & Follow-up is scheduled for implementation in Module 16. It tracks multi-encounter histories, plots physiological trends over months and years, and coordinates staff tasks for post-encounter follow-up. Interactive charting libraries and longitudinal care coordination workflows are not yet active in this frontend shell."
          verifiedFoundations={[
            "Relational Models: Patient, Encounter, and Observation entities (Module 3)",
            "Repositories: Longitudinal query methods in PatientRepository and EncounterRepository",
            "Timezone Integrity: UTC-enforced timestamp models preventing clinical sequencing errors",
            "Safety Distinction: Tasks designated strictly as internal staff actions, not direct patient advice",
          ]}
        />

        <section aria-labelledby="timeline-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="timeline-capabilities-heading" className={styles.sectionTitle}>
              Planned Longitudinal Care Capabilities
            </h2>
            <p className={styles.sectionSubtitle}>
              Temporal visualization and care continuity features planned in Module 16.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="12" cy="12" r="10" />
                  <polyline points="12 6 12 12 16 14" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Chronological Trajectory</h3>
              <p className={styles.pillarDescription}>
                Unified visual timeline organizing emergency visits, inpatient admissions, and outpatient
                consultations into a cohesive longitudinal clinical record.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Physiological Trend Tracking</h3>
              <p className={styles.pillarDescription}>
                Multi-series observation graphs plotting vitals (blood pressure, heart rate) and key lab
                biomarkers (HbA1c, eGFR, troponin) against standard clinical reference bands.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                  <line x1="16" y1="2" x2="16" y2="6" />
                  <line x1="8" y1="2" x2="8" y2="6" />
                  <line x1="3" y1="10" x2="21" y2="10" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Staff Follow-up Coordination</h3>
              <p className={styles.pillarDescription}>
                Internal staff task queues for scheduling follow-up imaging, tracking repeat laboratory
                orders, and confirming medication reconciliation across care transitions.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
