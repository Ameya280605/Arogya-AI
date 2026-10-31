import type { Metadata } from "next";
import { PageContainer } from "@/components/layout/PageContainer";
import { PlannedFeatureState } from "@/components/states";
import styles from "../page.module.css";

export const metadata: Metadata = {
  title: "Multi-Agent Orchestration — Arogya AI",
  description: "Deterministic LangGraph state machine, specialized clinical reasoning agents, and failure isolation.",
};

export default function AgentsPage() {
  return (
    <PageContainer
      title="Multi-Agent State Graph &amp; Orchestration"
      description="Deterministic state graph coordination, specialized clinical sub-agents, inter-agent consensus, and isolated execution lifecycles."
      breadcrumbs={[
        { label: "Overview", href: "/" },
        { label: "Multi-Agent State Graph" },
      ]}
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 11 Planned"
        >
          <span className={styles.stageDot} aria-hidden="true" />
          <span>Module 11: Planned</span>
        </div>
      }
    >
      <div className={styles.container}>
        <PlannedFeatureState
          moduleName="Module 11: Multi-Agent Orchestration"
          targetBlock="Block 3: AI Research & Multimodal Pipeline"
          statusText="Planned for a future module"
          description="Multi-Agent Orchestration is scheduled for implementation in Module 11. It builds a deterministic LangGraph state machine coordinating specialized research agents (Patient Context, Lab Interpreter, Imaging Adapter, Knowledge Retriever, and Critic). Multi-agent execution runners and live state graph transitions are not yet connected to this frontend shell."
          verifiedFoundations={[
            "Data Contracts: Standardized AgentResult schema specifications (Module 3)",
            "Run Lifecycles: AnalysisRun QUEUED, RUNNING, COMPLETED, FAILED states (Module 3)",
            "Timeout & Fault Isolation: Per-agent timeout boundaries and graceful fallbacks",
            "Orchestration Design: Deterministic LangGraph execution graph architecture (M11)",
          ]}
        />

        <section aria-labelledby="agents-capabilities-heading">
          <div className={styles.sectionHeading}>
            <h2 id="agents-capabilities-heading" className={styles.sectionTitle}>
              Planned Orchestration Architecture
            </h2>
            <p className={styles.sectionSubtitle}>
              Core agent graph nodes and deterministic routing planned in Module 11.
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="18" cy="5" r="3" />
                  <circle cx="6" cy="12" r="3" />
                  <circle cx="18" cy="19" r="3" />
                  <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
                  <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Deterministic State Machine</h3>
              <p className={styles.pillarDescription}>
                LangGraph state transitions with explicit node checkpoints, immutable run identifiers,
                and schema-validated data flow between execution steps.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Specialist Domain Sub-Agents</h3>
              <p className={styles.pillarDescription}>
                Partitioned agents with dedicated prompts: Patient History Summarizer, Lab Panel
                Interpreter, Medical Imaging Adapter, and Literature Evidence Retriever.
              </p>
            </article>

            <article className={styles.pillarCard}>
              <div className={styles.pillarIconContainer} aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
              </div>
              <h3 className={styles.pillarTitle}>Fault Isolation &amp; Timeouts</h3>
              <p className={styles.pillarDescription}>
                Sandboxed execution where individual sub-agent latency or network timeouts cannot crash
                the parent clinical workspace pipeline.
              </p>
            </article>
          </div>
        </section>
      </div>
    </PageContainer>
  );
}
