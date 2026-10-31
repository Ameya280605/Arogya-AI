import React from "react";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import type {
  PatientSummary,
  EncounterSummary,
  AnalysisSummary,
  PendingReviewQueueSummary,
} from "@/types/dashboard";
import styles from "./SummaryCard.module.css";

export type CardStatus = "ready" | "loading" | "unavailable" | "error";

export interface BreakdownItem {
  label: string;
  value: number | string;
}

export interface SummaryCardProps {
  /** Metric domain title */
  title: string;
  /** Contextual descriptive subtitle */
  subtitle?: string;
  /** Primary metric value (can be 0) */
  value?: number | string | null;
  /** Measurement unit or suffix */
  unit?: string;
  /** Optional badge rendered in top right */
  badge?: React.ReactNode;
  /** Visual domain icon */
  icon?: React.ReactNode;
  /** Sub-metric distribution breakdown items */
  breakdown?: BreakdownItem[];
  /** Component rendering lifecycle status */
  status?: CardStatus;
  /** Diagnostic or explanatory status message for loading/error/unavailable */
  statusMessage?: string;
  /** Explicit synthetic or demonstration provenance statement */
  provenance?: string;
  /** Additional architectural or disclaimer note */
  footerNote?: string;
}

/**
 * Reusable summary card component presenting overview metrics.
 * Complies with Arogya AI clinical design tokens and accessibility guidelines.
 */
export function SummaryCard({
  title,
  subtitle,
  value,
  unit,
  badge,
  icon,
  breakdown,
  status = "ready",
  statusMessage,
  provenance,
  footerNote,
}: SummaryCardProps) {
  // 1. Loading State
  if (status === "loading") {
    return (
      <article
        className={styles.card}
        role="region"
        aria-label={`${title} loading`}
        aria-busy="true"
      >
        <div className={styles.cardHeader}>
          <div className={styles.titleArea}>
            <Skeleton width="120px" height={16} />
            <Skeleton width="180px" height={12} />
          </div>
          <Skeleton width="36px" height={36} variant="circular" />
        </div>
        <div className={styles.valueContainer}>
          <Skeleton width="90px" height={40} />
        </div>
        <div className={styles.breakdownGrid}>
          <Skeleton width="60px" height={14} />
          <Skeleton width="60px" height={14} />
          <Skeleton width="60px" height={14} />
        </div>
      </article>
    );
  }

  // 2. Error State
  if (status === "error") {
    return (
      <article
        className={styles.card}
        role="alert"
        aria-label={`${title} metric load error`}
      >
        <div className={styles.cardHeader}>
          <div className={styles.titleArea}>
            <h3 className={styles.title}>{title}</h3>
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {icon && <div className={styles.iconContainer}>{icon}</div>}
        </div>
        <div className={styles.unavailableBox} style={{ borderColor: "var(--color-danger-border)" }}>
          <span className={styles.unavailableTitle} style={{ color: "var(--color-danger-fg)" }}>
            Metric Synchronization Error
          </span>
          <p className={styles.unavailableDesc}>
            {statusMessage || "Unable to retrieve aggregated metrics from service."}
          </p>
        </div>
      </article>
    );
  }

  // 3. Unavailable / Pending Integration State
  if (status === "unavailable") {
    return (
      <article
        className={styles.card}
        role="region"
        aria-label={`${title} integration pending`}
      >
        <div className={styles.cardHeader}>
          <div className={styles.titleArea}>
            <h3 className={styles.title}>{title}</h3>
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {icon && <div className={styles.iconContainer}>{icon}</div>}
        </div>
        <div className={styles.unavailableBox}>
          <span className={styles.unavailableTitle}>Integration Pending</span>
          <p className={styles.unavailableDesc}>
            {statusMessage || "Live aggregation endpoint scheduled for subsequent roadmap phase."}
          </p>
        </div>
        {provenance && (
          <div className={styles.provenanceBadge}>
            <span>Provenance:</span>
            <span>{provenance}</span>
          </div>
        )}
      </article>
    );
  }

  // 4. Ready / Populated State
  const formattedValue =
    typeof value === "number" ? value.toLocaleString("en-US") : value ?? "—";

  return (
    <article
      className={styles.card}
      role="region"
      aria-label={`${title} summary: ${formattedValue} ${unit || ""}`}
    >
      <div className={styles.cardHeader}>
        <div className={styles.titleArea}>
          <h3 className={styles.title}>{title}</h3>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          {badge}
          {icon && <div className={styles.iconContainer}>{icon}</div>}
        </div>
      </div>

      <div className={styles.valueContainer}>
        <span className={styles.value}>{formattedValue}</span>
        {unit && <span className={styles.unit}>{unit}</span>}
      </div>

      {breakdown && breakdown.length > 0 && (
        <div className={styles.breakdownGrid} role="list" aria-label={`${title} breakdown`}>
          {breakdown.map((item) => (
            <div key={item.label} className={styles.breakdownItem} role="listitem">
              <span className={styles.breakdownLabel}>{item.label}</span>
              <span className={styles.breakdownValue}>
                {typeof item.value === "number"
                  ? item.value.toLocaleString("en-US")
                  : item.value}
              </span>
            </div>
          ))}
        </div>
      )}

      {provenance && (
        <div className={styles.provenanceBadge}>
          <span style={{ color: "var(--color-text-tertiary)" }}>Data:</span>
          <span>{provenance}</span>
        </div>
      )}

      {footerNote && <p className={styles.footerNote}>{footerNote}</p>}
    </article>
  );
}

// ---------------------------------------------------------------------------
// Specialized Domain Wrappers Consuming Phase 5.1 Contracts
// ---------------------------------------------------------------------------

export interface DomainCardProps<T> {
  summary?: T | null;
  status?: CardStatus;
  statusMessage?: string;
  provenance?: string;
}

/**
 * Specialized Summary Card for Patient Cohort metrics.
 */
export function PatientSummaryCard({
  summary,
  status = "ready",
  statusMessage,
  provenance = "Synthetic seed cohort (Module 3)",
}: DomainCardProps<PatientSummary>) {
  if (!summary && status === "ready") {
    status = "unavailable";
  }

  return (
    <SummaryCard
      title="Patient Cohort"
      subtitle="Registered pseudonymous research subjects"
      value={summary ? summary.total_patients : null}
      unit="subjects"
      status={status}
      statusMessage={statusMessage}
      provenance={provenance}
      badge={<Badge variant="info">M6 Cohort</Badge>}
      icon={
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      }
      breakdown={
        summary
          ? [
              { label: "Synthetic", value: summary.synthetic_patients },
              { label: "Research", value: summary.research_cohort_patients },
            ]
          : undefined
      }
      footerNote="Zero-PHI policy enforced: pseudonymous research records only."
    />
  );
}

/**
 * Specialized Summary Card for Clinical Encounter metrics.
 */
export function EncounterSummaryCard({
  summary,
  status = "ready",
  statusMessage,
  provenance = "Synthetic seed encounters (Module 3)",
}: DomainCardProps<EncounterSummary>) {
  if (!summary && status === "ready") {
    status = "unavailable";
  }

  return (
    <SummaryCard
      title="Clinical Encounters"
      subtitle="Recorded longitudinal care interactions"
      value={summary ? summary.total_encounters : null}
      unit="events"
      status={status}
      statusMessage={statusMessage}
      provenance={provenance}
      badge={<Badge variant="neutral">Care Events</Badge>}
      icon={
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
        </svg>
      }
      breakdown={
        summary
          ? [
              { label: "Planned", value: summary.planned },
              { label: "In Progress", value: summary.in_progress },
              { label: "Completed", value: summary.completed },
              { label: "Cancelled", value: summary.cancelled },
            ]
          : undefined
      }
      footerNote="Chronological care encounters segregated from model outputs."
    />
  );
}

/**
 * Specialized Summary Card for AI Analysis Run executions.
 */
export function AnalysisSummaryCard({
  summary,
  status = "ready",
  statusMessage,
  provenance = "Evaluated analysis records (Module 3)",
}: DomainCardProps<AnalysisSummary>) {
  if (!summary && status === "ready") {
    status = "unavailable";
  }

  return (
    <SummaryCard
      title="AI Analysis Runs"
      subtitle="Research pipeline executions & model inferences"
      value={summary ? summary.total_runs : null}
      unit="runs"
      status={status}
      statusMessage={statusMessage}
      provenance={provenance}
      badge={<Badge variant="info">AI Pipeline</Badge>}
      icon={
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      }
      breakdown={
        summary
          ? [
              { label: "Completed", value: summary.by_status.completed },
              { label: "Abstained", value: summary.by_status.abstained },
              { label: "Running", value: summary.by_status.running },
              { label: "Queued", value: summary.by_status.queued },
              { label: "Failed", value: summary.by_status.failed },
            ]
          : undefined
      }
      footerNote={
        summary && summary.active_models_observed.length > 0
          ? `Active models: ${summary.active_models_observed.join(", ")}`
          : "Research model executions strictly segregated from ground-truth data."
      }
    />
  );
}

/**
 * Specialized Summary Card for Runs Requiring Clinical Review.
 * Uses strictly honest wording per Phase 5.2 guidelines.
 */
export function ReviewQueueSummaryCard({
  summary,
  status = "ready",
  statusMessage,
  provenance = "Completed/abstained candidate runs",
}: DomainCardProps<PendingReviewQueueSummary>) {
  if (!summary && status === "ready") {
    status = "unavailable";
  }

  return (
    <SummaryCard
      title="Runs Requiring Review"
      subtitle="Candidate model outputs awaiting clinician review"
      value={summary ? summary.pending_count : null}
      unit="candidates"
      status={status}
      statusMessage={statusMessage}
      provenance={provenance}
      badge={<Badge variant="warning">Human Review</Badge>}
      icon={
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      }
      breakdown={
        summary && summary.items.length > 0
          ? [
              {
                label: "Preview Items",
                value: `${summary.items.length} candidate${summary.items.length === 1 ? "" : "s"}`,
              },
              {
                label: "Abstained Flags",
                value: summary.items.filter((i) => i.abstained).length,
              },
            ]
          : undefined
      }
      footerNote="Candidate review queue; formal doctor sign-off workflow is deferred to Module 15."
    />
  );
}
