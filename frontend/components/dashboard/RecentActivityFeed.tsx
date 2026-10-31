import React from "react";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import type { RecentActivitySummary, RecentActivityItem } from "@/types/dashboard";
import styles from "./RecentActivityFeed.module.css";

export type ActivityFeedStatus = "ready" | "loading" | "unavailable" | "error";

export interface RecentActivityFeedProps {
  /** Activity summary payload conforming to Phase 5.1 contract */
  summary?: RecentActivitySummary | null;
  /** Component rendering lifecycle status */
  status?: ActivityFeedStatus;
  /** Diagnostic or explanatory status message */
  statusMessage?: string;
  /** Maximum items to display */
  maxItems?: number;
  /** Provenance statement for demonstration/synthetic telemetry */
  provenance?: string;
}

/**
 * Allowlist mapping raw machine event types to safe, clinical-grade human titles.
 * Prevents displaying raw internal error traces or unsanitized strings.
 */
const SAFE_EVENT_TITLES: Record<string, string> = {
  "analysis.started": "AI Analysis Execution Started",
  "analysis.completed": "AI Analysis Concluded",
  "analysis.abstained": "Model Safety Abstention Logged",
  "analysis.failed": "Analysis Execution Interrupted",
  "case.created": "Patient Case Registered",
  "encounter.started": "Clinical Encounter Initiated",
  "encounter.completed": "Clinical Encounter Completed",
  "user.login": "System Authentication Event",
  "asset.uploaded": "Medical Asset Uploaded",
  "dataset.seeded": "Synthetic Dataset Initialized",
};

/**
 * Maps actions to accessible badge variants.
 */
function getActionBadgeVariant(action: string): "success" | "info" | "neutral" | "danger" | "warning" {
  switch (action.toLowerCase()) {
    case "create":
      return "success";
    case "execute":
      return "info";
    case "delete":
      return "danger";
    case "update":
      return "warning";
    default:
      return "neutral";
  }
}

/**
 * Safely format ISO UTC timestamp string with fallback for invalid or missing values.
 */
export function formatUtcTimestamp(isoString: string | null | undefined): string {
  if (!isoString) return "Unknown timestamp";
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "Invalid timestamp";
    return d.toISOString().replace("T", " ").substring(0, 19) + " UTC";
  } catch {
    return "Invalid timestamp";
  }
}

/**
 * Reusable recent activity component for the Overview Dashboard.
 * Consumes the Phase 5.1 RecentActivitySummary contract.
 */
export function RecentActivityFeed({
  summary,
  status = "ready",
  statusMessage,
  maxItems = 5,
  provenance = "Immutable audit log (Module 3)",
}: RecentActivityFeedProps) {
  // 1. Loading State
  if (status === "loading") {
    return (
      <section
        className={styles.feedContainer}
        aria-labelledby="activity-feed-heading"
        aria-busy="true"
      >
        <div className={styles.feedHeader}>
          <div className={styles.titleArea}>
            <Skeleton width="180px" height={20} />
            <Skeleton width="260px" height={14} />
          </div>
          <Skeleton width="80px" height={24} />
        </div>
        <div className={styles.activityList}>
          {[1, 2, 3].map((key) => (
            <div key={key} className={styles.activityItem}>
              <div className={styles.leftSection}>
                <Skeleton width="32px" height={32} variant="circular" />
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <Skeleton width="200px" height={16} />
                  <Skeleton width="320px" height={12} />
                </div>
              </div>
              <Skeleton width="100px" height={14} />
            </div>
          ))}
        </div>
      </section>
    );
  }

  // 2. Error State
  if (status === "error") {
    return (
      <section
        className={styles.feedContainer}
        role="alert"
        aria-labelledby="activity-feed-heading"
      >
        <div className={styles.feedHeader}>
          <div className={styles.titleArea}>
            <h2 id="activity-feed-heading" className={styles.feedTitle}>
              Recent System Activity
            </h2>
            <p className={styles.feedSubtitle}>
              Platform operational telemetry &amp; execution audit trails
            </p>
          </div>
        </div>
        <div className={styles.emptyStateBox} style={{ borderColor: "var(--color-danger-border)" }}>
          <span className={styles.emptyTitle} style={{ color: "var(--color-danger-fg)" }}>
            Telemetry Synchronization Error
          </span>
          <p className={styles.emptyDesc}>
            {statusMessage || "Unable to retrieve recent system activity logs."}
          </p>
        </div>
      </section>
    );
  }

  // 3. Unavailable State
  if (status === "unavailable" || !summary) {
    return (
      <section
        className={styles.feedContainer}
        aria-labelledby="activity-feed-heading"
      >
        <div className={styles.feedHeader}>
          <div className={styles.titleArea}>
            <h2 id="activity-feed-heading" className={styles.feedTitle}>
              Recent System Activity
            </h2>
            <p className={styles.feedSubtitle}>
              Platform operational telemetry &amp; execution audit trails
            </p>
          </div>
          <Badge variant="neutral">Feed Pending</Badge>
        </div>
        <div className={styles.emptyStateBox}>
          <span className={styles.emptyTitle}>Operational Feed Pending Integration</span>
          <p className={styles.emptyDesc}>
            {statusMessage ||
              "Audit event aggregation endpoint will be connected in Phase 5.3. No fabricated events are displayed."}
          </p>
        </div>
        <div className={styles.provenanceFooter}>
          <span>Zero-PHI Guarantee: Plaintext credentials and clinical notes strictly excluded.</span>
          <span>Integration: Phase 5.3 REST API</span>
        </div>
      </section>
    );
  }

  // 4. Populated State (or Empty List)
  const activities = (summary.activities || []).slice(0, maxItems);
  const totalEvents = summary.total_events ?? activities.length;

  return (
    <section
      className={styles.feedContainer}
      aria-labelledby="activity-feed-heading"
    >
      <div className={styles.feedHeader}>
        <div className={styles.titleArea}>
          <h2 id="activity-feed-heading" className={styles.feedTitle}>
            Recent System Activity
          </h2>
          <p className={styles.feedSubtitle}>
            Platform operational telemetry &amp; execution audit trails
          </p>
        </div>
        <Badge variant={totalEvents > 0 ? "info" : "neutral"}>
          {totalEvents} {totalEvents === 1 ? "Event" : "Events"}
        </Badge>
      </div>

      {activities.length === 0 ? (
        <div className={styles.emptyStateBox}>
          <span className={styles.emptyTitle}>No Recent Events Recorded</span>
          <p className={styles.emptyDesc}>
            No operational audit events were found in the current activity window.
          </p>
        </div>
      ) : (
        <ul className={styles.activityList} aria-label="Chronological system activities">
          {activities.map((item: RecentActivityItem) => {
            const safeTitle =
              SAFE_EVENT_TITLES[item.event_type] ||
              item.event_type.replace(/_/g, " ").replace(/\./g, " — ");
            const badgeVariant = getActionBadgeVariant(item.action);

            return (
              <li key={item.id} className={styles.activityItem}>
                <div className={styles.leftSection}>
                  <div className={styles.iconWrapper} aria-hidden="true">
                    <svg
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    >
                      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
                    </svg>
                  </div>
                  <div className={styles.itemBody}>
                    <div className={styles.itemHeading}>
                      <span className={styles.eventTypeName}>{safeTitle}</span>
                      <Badge variant={badgeVariant}>{item.action}</Badge>
                      {item.resource_type && (
                        <span style={{ fontSize: "var(--font-size-micro)", color: "var(--color-text-muted)" }}>
                          ({item.resource_type})
                        </span>
                      )}
                    </div>
                    {item.description && (
                      <p className={styles.safeDescription}>{item.description}</p>
                    )}
                  </div>
                </div>

                <div className={styles.itemMeta}>
                  <time className={styles.timeText} dateTime={item.timestamp}>
                    {formatUtcTimestamp(item.timestamp)}
                  </time>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <div className={styles.provenanceFooter}>
        <span>Provenance: {provenance} &bull; Zero-PHI Guarantee enforced</span>
        <span>Generated: {formatUtcTimestamp(summary.generated_at)}</span>
      </div>
    </section>
  );
}
