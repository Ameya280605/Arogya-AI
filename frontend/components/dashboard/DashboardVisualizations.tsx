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
import type {
  AnalysisSummary,
  PendingReviewQueueSummary,
  AnalysisRunStatus,
} from "@/types/dashboard";
import type { DashboardFilterState } from "./DashboardFilterBar";
import styles from "./DashboardVisualizations.module.css";

export type VisualizationStatus = "ready" | "loading" | "unavailable" | "error";

export interface DashboardVisualizationsProps {
  /** Filtered or raw analysis summary */
  analysis?: AnalysisSummary | null;
  /** Filtered or raw review queue summary */
  reviews?: PendingReviewQueueSummary | null;
  /** Active dashboard filters */
  filters?: DashboardFilterState;
  /** Rendering lifecycle status */
  status?: VisualizationStatus;
  /** Explanatory status message */
  statusMessage?: string;
  /** Provenance statement */
  provenance?: string;
}

interface StatusItem {
  key: AnalysisRunStatus;
  label: string;
  count: number;
  percentage: number;
  colorVar: string;
}

/**
 * Reusable dashboard visualizations component.
 *
 * Implements accessible, filter-aware visual distributions for analysis run lifecycle
 * states and review queue model distributions.
 *
 * NOTE: Diagnostic performance charts (ROC curves, sensitivity/specificity) are
 * intentionally omitted per research prototype governance.
 */
export function DashboardVisualizations({
  analysis,
  reviews,
  filters,
  status = "ready",
  statusMessage,
  provenance = "Synthetic demonstration dataset (Module 3)",
}: DashboardVisualizationsProps) {
  // 1. Loading State
  if (status === "loading") {
    return (
      <section
        className={styles.visualizationsSection}
        aria-labelledby="dashboard-visualizations-heading"
        aria-busy="true"
      >
        <div className={styles.sectionHeader}>
          <div>
            <Skeleton width="240px" height={24} />
            <Skeleton width="360px" height={14} style={{ marginTop: "var(--space-2)" }} />
          </div>
        </div>

        <div className={styles.chartsGrid}>
          <div className={styles.chartCard}>
            <Skeleton width="180px" height={20} />
            <Skeleton width="100%" height={14} />
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", marginTop: "var(--space-2)" }}>
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <Skeleton width="120px" height={14} />
                  <Skeleton width="100%" height={10} />
                </div>
              ))}
            </div>
          </div>

          <div className={styles.chartCard}>
            <Skeleton width="180px" height={20} />
            <Skeleton width="100%" height={14} />
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)", marginTop: "var(--space-2)" }}>
              {[1, 2].map((i) => (
                <div key={i} style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <Skeleton width="140px" height={14} />
                  <Skeleton width="100%" height={10} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>
    );
  }

  // 2. Error State
  if (status === "error") {
    return (
      <section
        className={styles.visualizationsSection}
        role="alert"
        aria-labelledby="dashboard-visualizations-heading"
      >
        <div className={styles.sectionHeader}>
          <h2 id="dashboard-visualizations-heading" className={styles.sectionTitle}>
            Dashboard Visualizations
          </h2>
        </div>
        <div className={styles.emptyStateBox} style={{ borderColor: "var(--color-danger-border)" }}>
          <span className={styles.emptyTitle} style={{ color: "var(--color-danger-fg)" }}>
            Visualization Synchronization Error
          </span>
          <p className={styles.emptyDesc}>
            {statusMessage || "Unable to compute distribution metrics from data source."}
          </p>
        </div>
      </section>
    );
  }

  // 3. Unavailable State
  if (status === "unavailable" || !analysis) {
    return (
      <section
        className={styles.visualizationsSection}
        aria-labelledby="dashboard-visualizations-heading"
      >
        <div className={styles.sectionHeader}>
          <div>
            <h2 id="dashboard-visualizations-heading" className={styles.sectionTitle}>
              Dashboard Visualizations
            </h2>
            <p className={styles.sectionSubtitle}>
              Aggregate distributions across AI pipeline executions and review queues
            </p>
          </div>
          <Badge variant="neutral">Charts Pending</Badge>
        </div>

        <div className={styles.unavailableBox}>
          <span className={styles.unavailableTitle}>Visualizations Pending Backend Integration</span>
          <p className={styles.unavailableDesc}>
            {statusMessage ||
              "Aggregated chart telemetry will be supplied by live database group-by queries in Phase 5.5. No simulated trends are displayed."}
          </p>
        </div>
      </section>
    );
  }

  // 4. Populated State: Compute Chart 1 (Analysis Run Lifecycle Distribution)
  const totalRuns = analysis.total_runs;
  const statusItems: StatusItem[] = [
    {
      key: "completed",
      label: "Completed",
      count: analysis.by_status.completed,
      percentage: totalRuns > 0 ? Math.round((analysis.by_status.completed / totalRuns) * 100) : 0,
      colorVar: "var(--color-success-primary)",
    },
    {
      key: "abstained",
      label: "Abstained (Safety Flag)",
      count: analysis.by_status.abstained,
      percentage: totalRuns > 0 ? Math.round((analysis.by_status.abstained / totalRuns) * 100) : 0,
      colorVar: "var(--color-warning-primary)",
    },
    {
      key: "running",
      label: "Running",
      count: analysis.by_status.running,
      percentage: totalRuns > 0 ? Math.round((analysis.by_status.running / totalRuns) * 100) : 0,
      colorVar: "var(--color-info-primary)",
    },
    {
      key: "queued",
      label: "Queued",
      count: analysis.by_status.queued,
      percentage: totalRuns > 0 ? Math.round((analysis.by_status.queued / totalRuns) * 100) : 0,
      colorVar: "var(--color-text-muted)",
    },
    {
      key: "failed",
      label: "Failed",
      count: analysis.by_status.failed,
      percentage: totalRuns > 0 ? Math.round((analysis.by_status.failed / totalRuns) * 100) : 0,
      colorVar: "var(--color-danger-primary)",
    },
  ];

  // Compute Chart 2 (Review Candidates by Research Model)
  const reviewItems = reviews?.items || [];
  const modelCounts: Record<string, { count: number; versions: Set<string> }> = {};
  for (const item of reviewItems) {
    if (!modelCounts[item.model_name]) {
      modelCounts[item.model_name] = { count: 0, versions: new Set() };
    }
    modelCounts[item.model_name].count += 1;
    if (item.model_version) {
      modelCounts[item.model_name].versions.add(item.model_version);
    }
  }

  const modelEntries = Object.entries(modelCounts).map(([modelName, data]) => ({
    name: modelName,
    count: data.count,
    percentage: reviewItems.length > 0 ? Math.round((data.count / reviewItems.length) * 100) : 0,
    versions: Array.from(data.versions).join(", "),
  }));

  const isStatusFiltered = Boolean(filters && filters.status !== "all");

  return (
    <section
      className={styles.visualizationsSection}
      aria-labelledby="dashboard-visualizations-heading"
    >
      <div className={styles.sectionHeader}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
            <h2 id="dashboard-visualizations-heading" className={styles.sectionTitle}>
              Dashboard Visualizations
            </h2>
            <Badge variant="info">Phase 5.4 Active</Badge>
          </div>
          <p className={styles.sectionSubtitle}>
            Accessible distribution analytics responding dynamically to active date and status filters.
          </p>
        </div>
      </div>

      <div className={styles.chartsGrid}>
        {/* -------------------------------------------------------------------
            Chart 1: Analysis Run Status Distribution
            ------------------------------------------------------------------- */}
        <article className={styles.chartCard} aria-labelledby="chart-status-dist-heading">
          <div className={styles.chartHeader}>
            <h3 id="chart-status-dist-heading" className={styles.chartTitle}>
              Analysis Run Status Distribution
            </h3>
            <Badge variant={totalRuns > 0 ? "neutral" : "warning"} size="sm">
              {totalRuns} Total {totalRuns === 1 ? "Run" : "Runs"}
            </Badge>
          </div>
          <p className={styles.chartDescription}>
            Relative proportion of execution states recorded across research AI pipelines.
            {isStatusFiltered && ` (Filtered by status: "${filters?.status}")`}
          </p>

          {totalRuns === 0 ? (
            <div className={styles.emptyStateBox}>
              <span className={styles.emptyTitle}>No Analysis Runs</span>
              <p className={styles.emptyDesc}>
                No pipeline runs match the current filter parameters.
              </p>
            </div>
          ) : (
            <>
              {/* Visual Horizontal Distribution Bars */}
              <ul
                className={styles.distributionList}
                role="list"
                aria-label="Analysis run status distribution bars"
              >
                {statusItems.map((item) => {
                  const isHighlighted = !isStatusFiltered || filters?.status === item.key;
                  return (
                    <li key={item.key} className={styles.distributionItem} role="listitem">
                      <div className={styles.itemLabelRow}>
                        <span className={styles.itemLabel}>
                          <AnalysisStatusIndicator status={item.key} size="sm" withDot />
                        </span>
                        <span className={styles.itemValue}>
                          <strong>{item.count}</strong> ({item.percentage}%)
                        </span>
                      </div>
                      <div className={styles.barTrack} role="presentation">
                        <div
                          className={styles.barFill}
                          style={{
                            width: `${item.percentage}%`,
                            backgroundColor: item.colorVar,
                            opacity: isHighlighted ? 1 : 0.35,
                          }}
                          aria-hidden="true"
                        />
                      </div>
                    </li>
                  );
                })}
              </ul>

              {/* Accessible Data Table Alternative */}
              <div className={styles.tableSummaryBox}>
                <Table>
                  <TableCaption>
                    Tabular distribution data for analysis run execution states (Accessible alternative)
                  </TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">Execution State</TableHead>
                      <TableHead scope="col">Run Count</TableHead>
                      <TableHead scope="col">Cohort Share</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {statusItems.map((item) => (
                      <TableRow key={item.key}>
                        <TableCell>{item.label}</TableCell>
                        <TableCell>{item.count}</TableCell>
                        <TableCell>{item.percentage}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </article>

        {/* -------------------------------------------------------------------
            Chart 2: Review Candidates by Research Model
            ------------------------------------------------------------------- */}
        <article className={styles.chartCard} aria-labelledby="chart-model-dist-heading">
          <div className={styles.chartHeader}>
            <h3 id="chart-model-dist-heading" className={styles.chartTitle}>
              Review Candidates by Model
            </h3>
            <Badge variant={reviewItems.length > 0 ? "warning" : "neutral"} size="sm">
              {reviewItems.length} {reviewItems.length === 1 ? "Candidate" : "Candidates"}
            </Badge>
          </div>
          <p className={styles.chartDescription}>
            Candidate analysis runs awaiting clinical oversight grouped by model architecture.
          </p>

          {reviewItems.length === 0 ? (
            <div className={styles.emptyStateBox}>
              <span className={styles.emptyTitle}>No Review Candidates</span>
              <p className={styles.emptyDesc}>
                There are currently no review candidates matching the selected date or status criteria.
              </p>
            </div>
          ) : (
            <>
              {/* Visual Distribution List */}
              <ul
                className={styles.distributionList}
                role="list"
                aria-label="Review candidates by research model bars"
              >
                {modelEntries.map((entry) => (
                  <li key={entry.name} className={styles.distributionItem} role="listitem">
                    <div className={styles.itemLabelRow}>
                      <span className={styles.itemLabel}>
                        <code style={{ fontFamily: "var(--font-mono, monospace)", fontSize: "var(--font-size-body-sm)" }}>
                          {entry.name}
                        </code>
                        {entry.versions && (
                          <span style={{ fontSize: "var(--font-size-micro)", color: "var(--color-text-muted)" }}>
                            (v{entry.versions})
                          </span>
                        )}
                      </span>
                      <span className={styles.itemValue}>
                        <strong>{entry.count}</strong> ({entry.percentage}%)
                      </span>
                    </div>
                    <div className={styles.barTrack} role="presentation">
                      <div
                        className={styles.barFill}
                        style={{
                          width: `${entry.percentage}%`,
                          backgroundColor: "var(--color-brand-primary)",
                        }}
                        aria-hidden="true"
                      />
                    </div>
                  </li>
                ))}
              </ul>

              {/* Accessible Data Table Alternative */}
              <div className={styles.tableSummaryBox}>
                <Table>
                  <TableCaption>
                    Tabular breakdown of candidate review items by research model
                  </TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">Research Model</TableHead>
                      <TableHead scope="col">Versions</TableHead>
                      <TableHead scope="col">Candidate Runs</TableHead>
                      <TableHead scope="col">Queue Share</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {modelEntries.map((entry) => (
                      <TableRow key={entry.name}>
                        <TableCell>{entry.name}</TableCell>
                        <TableCell>{entry.versions || "—"}</TableCell>
                        <TableCell>{entry.count}</TableCell>
                        <TableCell>{entry.percentage}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </article>
      </div>

      {/* -----------------------------------------------------------------------
          Mandatory Research Safety Notice & Omitted Diagnostic Charts
          ----------------------------------------------------------------------- */}
      <div className={styles.boundaryBox} role="note">
        <span className={styles.boundaryTitle}>
          Research Prototype Visualization &amp; Clinical Safety Boundary:
        </span>
        <span className={styles.boundaryText}>
          Diagnostic performance benchmarks (ROC curves, sensitivity/specificity, and calibration plots)
          are intentionally omitted from the Overview Dashboard. Systematic algorithmic evaluation
          and multi-model benchmarking belong to Module 18 (AI Research Lab) and clinical validation is deferred.
          All visualizations above reflect {provenance}.
        </span>
      </div>
    </section>
  );
}
