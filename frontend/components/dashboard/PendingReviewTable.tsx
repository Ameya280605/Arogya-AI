import React from "react";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
} from "@/components/ui/Table";
import { AnalysisStatusIndicator } from "./AnalysisStatusIndicator";
import { formatUtcTimestamp } from "./RecentActivityFeed";
import type { PendingReviewQueueSummary, PendingReviewItem } from "@/types/dashboard";
import styles from "./PendingReviewTable.module.css";

export type ReviewTableStatus = "ready" | "loading" | "unavailable" | "error";

export interface PendingReviewTableProps {
  /** Pending review queue summary payload conforming to Phase 5.1 contract */
  summary?: PendingReviewQueueSummary | null;
  /** Component rendering lifecycle status */
  status?: ReviewTableStatus;
  /** Diagnostic or explanatory status message for loading/error/unavailable */
  statusMessage?: string;
  /** Provenance statement for demonstration/synthetic records */
  provenance?: string;
  /** Maximum number of review candidate items to render */
  maxItems?: number;
}

/**
 * Reusable table component displaying candidate analysis runs requiring review.
 *
 * Implements accessible, responsive tabular presentation based on Phase 5.1 contracts.
 * Strictly adheres to research prototype boundaries: does not claim formal doctor sign-offs,
 * reviewer assignment, or persistent amendment records (deferred to Module 15).
 */
export function PendingReviewTable({
  summary,
  status = "ready",
  statusMessage,
  provenance = "Completed/abstained candidate runs (Module 3)",
  maxItems = 10,
}: PendingReviewTableProps) {
  // 1. Loading State
  if (status === "loading") {
    return (
      <section
        className={styles.tableSection}
        aria-labelledby="review-candidates-heading"
        aria-busy="true"
      >
        <div className={styles.headerArea}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <Skeleton width="220px" height={24} />
              <Skeleton width="80px" height={20} />
            </div>
            <Skeleton width="340px" height={14} style={{ marginTop: "var(--space-2)" }} />
          </div>
        </div>

        <div className={styles.boundaryNotice}>
          <Skeleton width="180px" height={14} />
          <Skeleton width="100%" height={12} />
        </div>

        <Table>
          <TableCaption>Analysis runs requiring clinician review (Loading placeholder)</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead>Run Reference</TableHead>
              <TableHead>Subject ID</TableHead>
              <TableHead>Encounter</TableHead>
              <TableHead>Research Model</TableHead>
              <TableHead>Execution State</TableHead>
              <TableHead>Abstention</TableHead>
              <TableHead>Created (UTC)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {[1, 2, 3].map((key) => (
              <TableRow key={key}>
                <TableCell><Skeleton width="90px" height={16} /></TableCell>
                <TableCell><Skeleton width="110px" height={16} /></TableCell>
                <TableCell><Skeleton width="90px" height={16} /></TableCell>
                <TableCell><Skeleton width="140px" height={16} /></TableCell>
                <TableCell><Skeleton width="80px" height={16} /></TableCell>
                <TableCell><Skeleton width="70px" height={16} /></TableCell>
                <TableCell><Skeleton width="120px" height={16} /></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>
    );
  }

  // 2. Error State
  if (status === "error") {
    return (
      <section
        className={styles.tableSection}
        role="alert"
        aria-labelledby="review-candidates-heading"
      >
        <div className={styles.headerArea}>
          <div>
            <h2 id="review-candidates-heading" className={styles.title}>
              Analysis Runs Requiring Review
            </h2>
            <p className={styles.subtitle}>
              Candidate model outputs awaiting clinician review
            </p>
          </div>
        </div>
        <div className={styles.unavailableBox} style={{ borderColor: "var(--color-danger-border)" }}>
          <span className={styles.unavailableTitle} style={{ color: "var(--color-danger-fg)" }}>
            Review Candidate Synchronization Error
          </span>
          <p className={styles.unavailableDesc}>
            {statusMessage || "Unable to retrieve pending review candidates from service."}
          </p>
        </div>
      </section>
    );
  }

  // 3. Unavailable State
  if (status === "unavailable" || !summary) {
    return (
      <section
        className={styles.tableSection}
        aria-labelledby="review-candidates-heading"
      >
        <div className={styles.headerArea}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <h2 id="review-candidates-heading" className={styles.title}>
                Analysis Runs Requiring Review
              </h2>
              <Badge variant="neutral">Queue Pending</Badge>
            </div>
            <p className={styles.subtitle}>
              Candidate model outputs awaiting clinician review
            </p>
          </div>
        </div>

        <div className={styles.boundaryNotice}>
          <span className={styles.noticeTitle}>Research Prototype Review Boundary:</span>
          <span className={styles.noticeText}>
            The Phase 5.1 data contract identifies completed or abstained analysis runs as candidates for review. Formal clinician assignment, electronic sign-offs, and clinical amendment workflows belong to Module 15 (Doctor Review &amp; Feedback) and are not implemented here.
          </span>
        </div>

        <div className={styles.unavailableBox}>
          <span className={styles.unavailableTitle}>Review Candidate Queue Pending Backend Integration</span>
          <p className={styles.unavailableDesc}>
            {statusMessage ||
              "Triage aggregation queries will be connected in Phase 5.5. No simulated clinician decisions or fabricated review records are displayed."}
          </p>
        </div>

        <div className={styles.footerArea}>
          <span>Zero-PHI Guarantee: Candidate summaries omit unstructured clinical text.</span>
          <span>Integration: Phase 5.5 REST API</span>
        </div>
      </section>
    );
  }

  // 4. Populated State (or Empty Table)
  const items: PendingReviewItem[] = (summary.items || []).slice(0, maxItems);
  const pendingCount = summary.pending_count ?? items.length;

  return (
    <section
      className={styles.tableSection}
      aria-labelledby="review-candidates-heading"
    >
      <div className={styles.headerArea}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <h2 id="review-candidates-heading" className={styles.title}>
              Analysis Runs Requiring Review
            </h2>
            <Badge variant={pendingCount > 0 ? "warning" : "neutral"}>
              {pendingCount} {pendingCount === 1 ? "Candidate" : "Candidates"}
            </Badge>
          </div>
          <p className={styles.subtitle}>
            Candidate model outputs awaiting clinician review. Formal reviewer assignment and doctor sign-off workflows belong to Module 15.
          </p>
        </div>
      </div>

      {/* Mandatory Review Workflow Limitation Notice */}
      <div className={styles.boundaryNotice} role="note">
        <span className={styles.noticeTitle}>Research Prototype Review Boundary:</span>
        <span className={styles.noticeText}>
          The Phase 5.1 data contract identifies completed or abstained analysis runs as candidates for review. Formal clinician assignment, electronic sign-offs, and clinical amendment workflows belong to Module 15 (Doctor Review &amp; Feedback) and are not implemented here.
        </span>
      </div>

      {items.length === 0 ? (
        <div className={styles.emptyBox}>
          <span className={styles.emptyTitle}>No Review Candidates In Queue</span>
          <p className={styles.emptyDesc}>
            There are currently no analysis runs flagged as requiring clinician review in this cohort window.
          </p>
        </div>
      ) : (
        <Table>
          <TableCaption>
            Candidate AI analysis runs awaiting human clinician review (Phase 5.1 contract preview)
          </TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead scope="col">Run Reference</TableHead>
              <TableHead scope="col">Subject ID</TableHead>
              <TableHead scope="col">Care Encounter</TableHead>
              <TableHead scope="col">Research Model</TableHead>
              <TableHead scope="col">Execution State</TableHead>
              <TableHead scope="col">Abstention</TableHead>
              <TableHead scope="col">Submitted (UTC)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => {
              const shortId = item.run_id ? item.run_id.substring(0, 8) : "UNKNOWN";
              return (
                <TableRow key={item.run_id}>
                  {/* 1. Run Identifier (Shortened safe hash) */}
                  <TableCell>
                    <code
                      className={styles.runIdCode}
                      title={`Full Run UUID: ${item.run_id}`}
                      aria-label={`Run ID ${item.run_id}`}
                    >
                      RUN-{shortId}
                    </code>
                  </TableCell>

                  {/* 2. Patient / Subject Identifier */}
                  <TableCell>
                    <span style={{ fontWeight: "var(--font-weight-medium)" }}>
                      {item.patient_id}
                    </span>
                  </TableCell>

                  {/* 3. Care Encounter */}
                  <TableCell>
                    {item.encounter_id ? (
                      <span style={{ color: "var(--color-text-secondary)" }}>
                        {item.encounter_id}
                      </span>
                    ) : (
                      <span style={{ color: "var(--color-text-muted)", fontStyle: "italic" }}>
                        Unassociated
                      </span>
                    )}
                  </TableCell>

                  {/* 4. Model Name & Version */}
                  <TableCell>
                    <div className={styles.modelSpec}>
                      <span className={styles.modelName}>{item.model_name}</span>
                      <span className={styles.modelVersion}>v{item.model_version}</span>
                    </div>
                  </TableCell>

                  {/* 5. Execution Lifecycle Status */}
                  <TableCell>
                    <AnalysisStatusIndicator status={item.status} size="sm" withDot />
                  </TableCell>

                  {/* 6. Abstention Indicator */}
                  <TableCell>
                    {item.abstained ? (
                      <Badge variant="warning" size="sm" withDot>
                        Abstained
                      </Badge>
                    ) : (
                      <Badge variant="neutral" size="sm">
                        Normal
                      </Badge>
                    )}
                  </TableCell>

                  {/* 7. Creation Timestamp */}
                  <TableCell className={styles.timestampCell}>
                    <time dateTime={item.created_at}>
                      {formatUtcTimestamp(item.created_at)}
                    </time>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      <div className={styles.footerArea}>
        <span>Provenance: {provenance} &bull; Zero-PHI Guarantee enforced</span>
        <span>Generated: {formatUtcTimestamp(summary.generated_at)}</span>
      </div>
    </section>
  );
}
