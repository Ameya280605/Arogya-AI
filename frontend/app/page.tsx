"use client";

import React, { useState, useMemo, useEffect } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import {
  Button,
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogBody,
  DialogFooter,
  DialogClose,
  FormField,
  Input,
  Checkbox,
  Skeleton,
  Toast,
} from "@/components/ui";
import {
  LoadingState,
  EmptyState,
  ErrorState,
  AccessDeniedState,
} from "@/components/states";
import {
  PatientSummaryCard,
  EncounterSummaryCard,
  AnalysisSummaryCard,
  ReviewQueueSummaryCard,
  RecentActivityFeed,
  PendingReviewTable,
  DashboardFilterBar,
  DashboardVisualizations,
  type CardStatus,
  type DashboardFilterState,
  DEFAULT_FILTER_STATE,
} from "@/components/dashboard";
import {
  fetchDashboardOverview,
  DashboardApiError,
} from "@/services/dashboard";
import type {
  PatientSummary,
  EncounterSummary,
  AnalysisSummary,
  PendingReviewQueueSummary,
  RecentActivitySummary,
  DashboardOverviewResponse,
} from "@/types/dashboard";
import styles from "./page.module.css";

// ---------------------------------------------------------------------------
// Documented Synthetic Demonstration Datasets (Module 3 Seed Cohort)
// Zero-PHI Guaranteed: Values strictly correspond to Module 3 seed definitions.
// ---------------------------------------------------------------------------
const DEMO_PATIENTS: PatientSummary = {
  total_patients: 10,
  synthetic_patients: 10,
  research_cohort_patients: 0,
  generated_at: "2026-01-10T08:00:00Z",
};

const DEMO_ENCOUNTERS: EncounterSummary = {
  total_encounters: 4,
  planned: 1,
  in_progress: 1,
  completed: 2,
  cancelled: 0,
  reporting_period_start: "2026-01-01T00:00:00Z",
  reporting_period_end: "2026-01-31T23:59:59Z",
  generated_at: "2026-01-15T10:00:00Z",
};

const DEMO_ANALYSIS: AnalysisSummary = {
  total_runs: 4,
  by_status: {
    queued: 0,
    running: 1,
    completed: 2,
    failed: 0,
    abstained: 1,
  },
  active_models_observed: ["chexnet-v2-research", "clinical-bert-ner"],
  generated_at: "2026-01-15T12:00:00Z",
};

const DEMO_REVIEWS: PendingReviewQueueSummary = {
  pending_count: 3,
  items: [
    {
      run_id: "7b0a88df-2b48-4cb3-9111-c9fe00000001",
      patient_id: "SYNTH-PAT-0001",
      encounter_id: "SYNTH-ENC-0001",
      model_name: "chexnet-v2-research",
      model_version: "2.1.0",
      status: "completed",
      abstained: false,
      created_at: "2026-01-15T11:00:00Z",
    },
    {
      run_id: "7b0a88df-2b48-4cb3-9111-c9fe00000002",
      patient_id: "SYNTH-PAT-0002",
      encounter_id: "SYNTH-ENC-0002",
      model_name: "clinical-bert-ner",
      model_version: "1.4.0",
      status: "abstained",
      abstained: true,
      created_at: "2026-01-15T11:30:00Z",
    },
    {
      run_id: "7b0a88df-2b48-4cb3-9111-c9fe00000003",
      patient_id: "SYNTH-PAT-0003",
      encounter_id: null,
      model_name: "chexnet-v2-research",
      model_version: "2.1.0",
      status: "completed",
      abstained: false,
      created_at: "2026-01-15T12:00:00Z",
    },
  ],
  generated_at: "2026-01-15T12:00:00Z",
};

const DEMO_ACTIVITY: RecentActivitySummary = {
  total_events: 3,
  activities: [
    {
      id: "evt-003",
      event_type: "analysis.abstained",
      action: "execute",
      resource_type: "analysis_run",
      resource_id: "7b0a88df-2b48-4cb3-9111-c9fe00000002",
      description: "Model safety filter triggered; abstention logged for clinician review",
      timestamp: "2026-01-15T11:30:00Z",
    },
    {
      id: "evt-002",
      event_type: "analysis.completed",
      action: "execute",
      resource_type: "analysis_run",
      resource_id: "7b0a88df-2b48-4cb3-9111-c9fe00000001",
      description: "Automated feature-attribution inference completed",
      timestamp: "2026-01-15T11:00:00Z",
    },
    {
      id: "evt-001",
      event_type: "encounter.completed",
      action: "update",
      resource_type: "encounter",
      resource_id: "SYNTH-ENC-0001",
      description: "Clinical encounter marked completed for synthetic cohort",
      timestamp: "2026-01-15T10:00:00Z",
    },
  ],
  generated_at: "2026-01-15T12:00:00Z",
};

/**
 * Utility helper to determine if an ISO timestamp falls within UTC date boundaries.
 * Handles boundary edge-cases and invalid dates safely.
 */
function isTimestampInDateRange(
  isoTimestamp: string,
  startDate?: string,
  endDate?: string
): boolean {
  if (!isoTimestamp) return false;
  try {
    const time = new Date(isoTimestamp).getTime();
    if (isNaN(time)) return false;

    if (startDate) {
      const startMs = new Date(`${startDate}T00:00:00.000Z`).getTime();
      if (!isNaN(startMs) && time < startMs) {
        return false;
      }
    }

    if (endDate) {
      const endMs = new Date(`${endDate}T23:59:59.999Z`).getTime();
      if (!isNaN(endMs) && time > endMs) {
        return false;
      }
    }

    return true;
  } catch {
    return false;
  }
}

export interface HomeProps {
  initialMode?: "live" | "demo" | "unavailable" | "loading";
}

export default function Home({
  initialMode = "live",
}: HomeProps = {}) {
  const [consentChecked, setConsentChecked] = useState(false);
  const [simulatedErrorResolved, setSimulatedErrorResolved] = useState(false);
  const [viewMode, setViewMode] = useState<"live" | "demo" | "unavailable" | "loading">(initialMode);
  const [filters, setFilters] = useState<DashboardFilterState>(DEFAULT_FILTER_STATE);
  const [liveData, setLiveData] = useState<DashboardOverviewResponse | null>(null);
  const [isFetchingLive, setIsFetchingLive] = useState(false);
  const [liveError, setLiveError] = useState<DashboardApiError | Error | null>(null);
  const [refetchTrigger, setRefetchTrigger] = useState(0);

  // Live database aggregation fetch effect
  useEffect(() => {
    if (viewMode !== "live") {
      return;
    }

    const controller = new AbortController();
    let cancelled = false;

    async function loadData() {
      setIsFetchingLive(true);
      setLiveError(null);
      try {
        const result = await fetchDashboardOverview({
          filters: {
            startDate: filters.startDate || undefined,
            endDate: filters.endDate || undefined,
            status: filters.status,
          },
          signal: controller.signal,
        });
        if (!cancelled) {
          setLiveData(result);
          setIsFetchingLive(false);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setIsFetchingLive(false);
        if (err instanceof Error && err.name === "AbortError") {
          return;
        }
        setLiveError(err instanceof Error ? err : new Error(String(err)));
      }
    }

    loadData();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [viewMode, filters, refetchTrigger]);

  // Dynamically filtered analysis summary (Synthetic Demo Fallback)
  const filteredAnalysis = useMemo<AnalysisSummary>(() => {
    const inDateRange = isTimestampInDateRange(
      DEMO_ANALYSIS.generated_at,
      filters.startDate,
      filters.endDate
    );

    if (!inDateRange) {
      return {
        ...DEMO_ANALYSIS,
        total_runs: 0,
        by_status: {
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          abstained: 0,
        },
      };
    }

    if (filters.status === "all") {
      return DEMO_ANALYSIS;
    }

    const count = DEMO_ANALYSIS.by_status[filters.status] ?? 0;
    return {
      ...DEMO_ANALYSIS,
      total_runs: count,
      by_status: {
        queued: filters.status === "queued" ? count : 0,
        running: filters.status === "running" ? count : 0,
        completed: filters.status === "completed" ? count : 0,
        failed: filters.status === "failed" ? count : 0,
        abstained: filters.status === "abstained" ? count : 0,
      },
    };
  }, [filters]);

  // Dynamically filtered review queue items (Synthetic Demo Fallback)
  const filteredReviews = useMemo<PendingReviewQueueSummary>(() => {
    const items = DEMO_REVIEWS.items.filter((item) => {
      if (filters.status !== "all" && item.status !== filters.status) {
        return false;
      }
      if (!isTimestampInDateRange(item.created_at, filters.startDate, filters.endDate)) {
        return false;
      }
      return true;
    });

    return {
      ...DEMO_REVIEWS,
      pending_count: items.length,
      items,
    };
  }, [filters]);

  // Dynamically filtered activity feed (Synthetic Demo Fallback)
  const filteredActivity = useMemo<RecentActivitySummary>(() => {
    const activities = DEMO_ACTIVITY.activities.filter((act) => {
      if (filters.status !== "all") {
        if (
          act.resource_type === "analysis_run" &&
          act.event_type !== `analysis.${filters.status}`
        ) {
          return false;
        }
      }
      if (!isTimestampInDateRange(act.timestamp, filters.startDate, filters.endDate)) {
        return false;
      }
      return true;
    });

    return {
      ...DEMO_ACTIVITY,
      total_events: activities.length,
      activities,
    };
  }, [filters]);

  // Compute presentation state and dataset bindings
  let effectiveStatus: CardStatus = "ready";
  if (viewMode === "loading") {
    effectiveStatus = "loading";
  } else if (viewMode === "unavailable") {
    effectiveStatus = "unavailable";
  } else if (viewMode === "live") {
    if (isFetchingLive && !liveData) {
      effectiveStatus = "loading";
    } else if (liveError) {
      effectiveStatus =
        liveError instanceof DashboardApiError && liveError.isUnavailable
          ? "unavailable"
          : "error";
    } else {
      effectiveStatus = "ready";
    }
  } else {
    // "demo"
    effectiveStatus = "ready";
  }

  const currentPatients = viewMode === "live" && liveData ? liveData.patients : DEMO_PATIENTS;
  const currentEncounters = viewMode === "live" && liveData ? liveData.encounters : DEMO_ENCOUNTERS;
  const currentAnalysis = viewMode === "live" && liveData ? liveData.analysis : filteredAnalysis;
  const currentReviews = viewMode === "live" && liveData ? liveData.reviews : filteredReviews;
  const currentActivity = viewMode === "live" && liveData ? liveData.recent_activity : filteredActivity;

  const currentProvenance =
    viewMode === "live"
      ? "Live PostgreSQL Aggregation (Phase 5.5)"
      : "Synthetic seed cohort (Module 3)";

  return (
    <PageContainer
      title="Clinical Intelligence & Decision Support"
      description="A modular healthcare intelligence and clinical decision-support research prototype investigating multimodal patient context, diagnostic assistance, and structured evidence synthesis for clinical research."
      breadcrumbs={[{ label: "Overview" }]}
      badge={
        <Badge variant="success" withDot>
          Module 5: Aggregation API Integrated (Phase 5.5)
        </Badge>
      }
    >
      <div className={styles.container}>
        {/* Mandatory Clinical Safety & Research Disclaimer */}
        <section
          className={styles.disclaimerBox}
          role="region"
          aria-labelledby="disclaimer-title"
        >
          <svg
            className={styles.disclaimerIcon}
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          <div className={styles.disclaimerBody}>
            <h2 id="disclaimer-title" className={styles.disclaimerTitle}>
              Research Prototype &amp; Human Review Notice
            </h2>
            <p className={styles.disclaimerText}>
              Arogya AI is an academic and investigative research prototype under active
              development. It is not a certified medical device and does not provide
              autonomous clinical diagnosis, prognostic certainty, or automated treatment
              plans. All clinical summaries, inferences, and analytics generated by future
              modules are intended strictly for evaluation and review by qualified healthcare
              professionals.
            </p>
          </div>
        </section>

        {/* Overview Dashboard Metrics & Recent Activity — Module 5 (Phase 5.2) */}
        <section aria-labelledby="overview-metrics-heading">
          <div className={styles.sectionHeading}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-3)" }}>
              <div>
                <h2 id="overview-metrics-heading" className={styles.sectionTitle}>
                  Clinical Overview &amp; Research Metrics
                </h2>
                <p className={styles.sectionSubtitle}>
                  Overview summary cards and chronological operational activity consuming Phase 5.1 data contracts.
                </p>
              </div>

              {/* Lifecycle State Inspection Controls */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "var(--space-2)",
                  flexWrap: "wrap",
                }}
                role="group"
                aria-label="Dashboard presentation state switcher"
              >
                <span
                  style={{
                    fontSize: "var(--font-size-body-sm)",
                    color: "var(--color-text-muted)",
                    marginRight: "var(--space-1)",
                  }}
                >
                  View Mode:
                </span>
                <Button
                  size="sm"
                  variant={viewMode === "live" ? "primary" : "outline"}
                  onClick={() => {
                    setViewMode("live");
                    setRefetchTrigger((p) => p + 1);
                  }}
                  aria-pressed={viewMode === "live"}
                >
                  Live Database
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === "demo" ? "primary" : "outline"}
                  onClick={() => setViewMode("demo")}
                  aria-pressed={viewMode === "demo"}
                >
                  Synthetic Demo
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === "unavailable" ? "primary" : "outline"}
                  onClick={() => setViewMode("unavailable")}
                  aria-pressed={viewMode === "unavailable"}
                >
                  Integration Pending
                </Button>
                <Button
                  size="sm"
                  variant={viewMode === "loading" ? "primary" : "outline"}
                  onClick={() => setViewMode("loading")}
                  aria-pressed={viewMode === "loading"}
                >
                  Loading Skeleton
                </Button>
              </div>
            </div>
          </div>

          {/* Truthful Provenance Banner */}
          <div
            style={{
              padding: "var(--space-3) var(--space-4)",
              marginBottom: "var(--space-4)",
              backgroundColor: "var(--color-bg-subtle)",
              border: "1px solid var(--color-border-subtle)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              flexWrap: "wrap",
              gap: "var(--space-2)",
              fontSize: "var(--font-size-body-sm)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
              <Badge
                variant={
                  viewMode === "live"
                    ? liveError
                      ? "danger"
                      : isFetchingLive
                      ? "warning"
                      : liveData
                      ? "success"
                      : "info"
                    : viewMode === "demo"
                    ? "info"
                    : "neutral"
                }
              >
                {viewMode === "live"
                  ? liveError
                    ? "Live Aggregation Error"
                    : isFetchingLive
                    ? "Connecting to Live API"
                    : liveData
                    ? "Live Database (Phase 5.5)"
                    : "Demonstration Provenance"
                  : viewMode === "demo"
                  ? "Demonstration Provenance"
                  : viewMode === "unavailable"
                  ? "Phase 5.5 Scheduled"
                  : "Simulated Fetch"}
              </Badge>
              <span style={{ color: "var(--color-text-secondary)" }}>
                {viewMode === "live"
                  ? liveError
                    ? `Live aggregation failed (${liveError.message}). Real-time clinical metrics are never fabricated.`
                    : isFetchingLive
                    ? "Querying GET /api/v1/dashboard/overview to aggregate real-time database records..."
                    : liveData
                    ? "Connected to backend API (GET /api/v1/dashboard/overview). Values reflect live database records."
                    : "Values below reflect seeded synthetic records (SYNTH-PAT-0001 cohort from Module 3). Real-time clinical metrics are never fabricated."
                  : viewMode === "demo"
                  ? "Values below reflect seeded synthetic records (SYNTH-PAT-0001 cohort from Module 3). Real-time clinical metrics are never fabricated."
                  : viewMode === "unavailable"
                  ? "Simulating truthful unavailable state for integration testing."
                  : "Rendering accessible skeleton placeholders simulating asynchronous metric retrieval."}
              </span>
            </div>
            <span style={{ color: "var(--color-text-tertiary)", fontSize: "var(--font-size-micro)" }}>
              Contract: Phase 5.1 &bull; REST API: Phase 5.5
            </span>
          </div>

          {/* Honest Error State Notification for Live Mode */}
          {viewMode === "live" && liveError && (
            <div style={{ marginBottom: "var(--space-5)" }}>
              <ErrorState
                title={
                  liveError instanceof DashboardApiError && liveError.isUnavailable
                    ? "Database Persistence Unavailable (HTTP 503)"
                    : "Dashboard API Connection Failure"
                }
                message={liveError.message}
                errorCode={
                  liveError instanceof DashboardApiError ? liveError.code : "ERR_API_FETCH"
                }
                onRetry={() => setRefetchTrigger((p) => p + 1)}
                retryLabel="Retry Live Request"
                secondaryAction={
                  <Button size="sm" variant="outline" onClick={() => setViewMode("demo")}>
                    Switch to Synthetic Demo
                  </Button>
                }
              />
            </div>
          )}

          {/* Dashboard Filter Bar — Module 5 (Phase 5.4 - 5.5) */}
          <div style={{ marginBottom: "var(--space-5)" }}>
            <DashboardFilterBar
              filters={filters}
              onFilterChange={setFilters}
              onReset={() => setFilters(DEFAULT_FILTER_STATE)}
              disabled={effectiveStatus === "loading" || (viewMode === "live" && isFetchingLive)}
              provenance={
                viewMode === "live"
                  ? "Live database query (Phase 5.5)"
                  : "Synthetic seed cohort (Module 3)"
              }
            />
          </div>

          {/* Empty Results State for Live Mode */}
          {viewMode === "live" && liveData && liveData.analysis.total_runs === 0 && (
            <div style={{ marginBottom: "var(--space-5)" }}>
              <EmptyState
                preset="runs"
                title="No Records Found for Filter Criteria"
                description={`No analysis runs or review candidates match the active filters (status: ${filters.status}, date range: ${filters.startDate || 'start'} to ${filters.endDate || 'end'}).`}
                action={{
                  label: "Reset Filters",
                  onClick: () => setFilters(DEFAULT_FILTER_STATE),
                  variant: "secondary",
                }}
                notice="Live query completed successfully with 0 matching rows."
              />
            </div>
          )}

          {/* 4 Summary Domain Cards */}
          <div className={styles.cardsGrid} style={{ marginBottom: "var(--space-6)" }}>
            <PatientSummaryCard
              summary={effectiveStatus === "ready" ? currentPatients : null}
              status={effectiveStatus}
              provenance={currentProvenance}
            />
            <EncounterSummaryCard
              summary={effectiveStatus === "ready" ? currentEncounters : null}
              status={effectiveStatus}
              provenance={currentProvenance}
            />
            <AnalysisSummaryCard
              summary={effectiveStatus === "ready" ? currentAnalysis : null}
              status={effectiveStatus}
              provenance={currentProvenance}
            />
            <ReviewQueueSummaryCard
              summary={effectiveStatus === "ready" ? currentReviews : null}
              status={effectiveStatus}
              provenance={
                viewMode === "live"
                  ? "Live completed/abstained candidate runs"
                  : "Completed/abstained candidate runs"
              }
            />
          </div>

          {/* Dashboard Visualizations & Lifecycle Distributions — Module 5 (Phase 5.4) */}
          <div style={{ marginBottom: "var(--space-6)" }}>
            <DashboardVisualizations
              analysis={effectiveStatus === "ready" ? currentAnalysis : null}
              reviews={effectiveStatus === "ready" ? currentReviews : null}
              filters={filters}
              status={effectiveStatus}
              provenance={
                viewMode === "live"
                  ? "Filtered live database records (Phase 5.5)"
                  : "Filtered synthetic seed cohort (Module 3)"
              }
            />
          </div>

          {/* Pending Review Candidates Table — Module 5 (Phase 5.3) */}
          <div style={{ marginBottom: "var(--space-6)" }}>
            <PendingReviewTable
              summary={effectiveStatus === "ready" ? currentReviews : null}
              status={effectiveStatus}
              provenance={
                viewMode === "live"
                  ? "Live completed/abstained candidate runs (Phase 5.5)"
                  : "Completed/abstained candidate runs (Module 3)"
              }
              maxItems={5}
            />
          </div>

          {/* Recent System Activity Feed */}
          <RecentActivityFeed
            summary={effectiveStatus === "ready" ? currentActivity : null}
            status={effectiveStatus}
            provenance={
              viewMode === "live"
                ? "Live audit events from persistence (Phase 5.5)"
                : "Immutable audit log (Module 3)"
            }
            maxItems={5}
          />
        </section>

        {/* Architectural Research Directions Section — Demonstrating Card Composition */}
        <section aria-labelledby="pillars-heading">
          <div className={styles.sectionHeading}>
            <h2 id="pillars-heading" className={styles.sectionTitle}>
              Architectural Research Directions
            </h2>
            <p className={styles.sectionSubtitle}>
              Core domain capabilities planned across the Arogya AI modular roadmap (rendered via Card primitives).
            </p>
          </div>

          <div className={styles.pillarsGrid}>
            <Card as="article">
              <CardHeader>
                <div className={styles.pillarIconContainer} aria-hidden="true">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <polyline points="10 9 9 9 8 9" />
                  </svg>
                </div>
                <CardTitle as="h3">Multimodal Context</CardTitle>
                <CardDescription>
                  Longitudinal patient timelines integrating laboratory observations, clinical
                  encounter notes, and medical imaging into a cohesive profile.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card as="article">
              <CardHeader>
                <div className={styles.pillarIconContainer} aria-hidden="true">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                </div>
                <CardTitle as="h3">Explainable Analytics</CardTitle>
                <CardDescription>
                  Feature-attribution explanations (SHAP) and saliency heatmaps (Grad-CAM)
                  to preserve algorithmic uncertainty and prevent overconfident conclusions.
                </CardDescription>
              </CardHeader>
            </Card>

            <Card as="article">
              <CardHeader>
                <div className={styles.pillarIconContainer} aria-hidden="true">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                </div>
                <CardTitle as="h3">Human-in-the-Loop</CardTitle>
                <CardDescription>
                  Interactive clinician review and critique interfaces where clinical users
                  retain absolute sovereignty over acceptance, refinement, or rejection of findings.
                </CardDescription>
              </CardHeader>
            </Card>
          </div>
        </section>

        {/* Technical Foundation Specifications — Demonstrating Table Primitive */}
        <section aria-labelledby="foundation-table-heading">
          <div className={styles.sectionHeading}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-2)" }}>
              <h2 id="foundation-table-heading" className={styles.sectionTitle}>
                Monorepo Technical Foundation
              </h2>
              <div style={{ display: "flex", gap: "var(--space-2)" }}>
                <Badge variant="success" withDot>Verified Stack</Badge>
                <Badge variant="neutral">Next.js 16.4</Badge>
              </div>
            </div>
            <p className={styles.sectionSubtitle}>
              Core architecture and component specifications verified in Modules 1–4 (rendered via Table primitive).
            </p>
          </div>

          <Table>
            <TableCaption>Arogya AI Monorepo Foundation &amp; Component Verification Matrix</TableCaption>
            <TableHeader>
              <TableRow>
                <TableHead>Architecture Layer</TableHead>
                <TableHead>Primary Technology</TableHead>
                <TableHead>Module</TableHead>
                <TableHead>Readiness Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow>
                <TableCell>Backend Platform</TableCell>
                <TableCell>FastAPI, Pydantic v2, Python 3.14</TableCell>
                <TableCell>Module 2</TableCell>
                <TableCell><Badge variant="success">Verified (146 Tests)</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Database &amp; Persistence</TableCell>
                <TableCell>PostgreSQL, SQLAlchemy 2.0, Alembic</TableCell>
                <TableCell>Module 3</TableCell>
                <TableCell><Badge variant="success">Verified &amp; Seeded</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Application Shell</TableCell>
                <TableCell>Next.js 16 App Router, React 19</TableCell>
                <TableCell>Module 4 (Phase 4.3)</TableCell>
                <TableCell><Badge variant="success">Responsive Shell Active</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>UI Component Primitives</TableCell>
                <TableCell>Vanilla CSS Tokens, Strict TypeScript</TableCell>
                <TableCell>Module 4 (Phase 4.4)</TableCell>
                <TableCell><Badge variant="success">Phase 4.4 Primitives Active</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Application State Primitives</TableCell>
                <TableCell>Loading, Empty, Error, Access-Denied, Planned</TableCell>
                <TableCell>Module 4 (Phase 4.5)</TableCell>
                <TableCell><Badge variant="success">Phase 4.5 Active</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Complete Route Architecture</TableCell>
                <TableCell>Next.js 16 App Router (16 User-Facing Routes, 21 Modules)</TableCell>
                <TableCell>Module 4 (Phase 4.6)</TableCell>
                <TableCell><Badge variant="success">Architecture Established</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Quality &amp; Navigation Verification</TableCell>
                <TableCell>Responsive Drawer, Accessibility Regressions, 69 Tests</TableCell>
                <TableCell>Module 4 (Phase 4.7)</TableCell>
                <TableCell><Badge variant="success">Module 4 Complete (69 Tests)</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Overview Dashboard</TableCell>
                <TableCell>Summary Cards &amp; Recent Activity (Phase 5.1 Contracts)</TableCell>
                <TableCell>Module 5 (Phase 5.2)</TableCell>
                <TableCell><Badge variant="success">Phase 5.2 Active</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Review Candidates &amp; Status</TableCell>
                <TableCell>Pending-Review Table &amp; Analysis Status Indicators</TableCell>
                <TableCell>Module 5 (Phase 5.3)</TableCell>
                <TableCell><Badge variant="success">Phase 5.3 Active</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Dashboard Filters &amp; Visualizations</TableCell>
                <TableCell>UTC Date/Status Filters &amp; Accessible Lifecycle Distribution Charts</TableCell>
                <TableCell>Module 5 (Phase 5.4)</TableCell>
                <TableCell><Badge variant="success">Phase 5.4 Active</Badge></TableCell>
              </TableRow>
              <TableRow>
                <TableCell>Dashboard API Aggregation</TableCell>
                <TableCell>FastAPI Aggregation Endpoint, PostgreSQL Aggregation &amp; Next.js Client</TableCell>
                <TableCell>Module 5 (Phase 5.5)</TableCell>
                <TableCell><Badge variant="success">Phase 5.5 Active</Badge></TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </section>

        {/* UI Component Primitives & States Showcase — Demonstrating Tabs, Dialog, Form, States */}
        <section aria-labelledby="primitives-showcase-heading">
          <div className={styles.sectionHeading}>
            <h2 id="primitives-showcase-heading" className={styles.sectionTitle}>
              UI Components &amp; Application States Showcase
            </h2>
            <p className={styles.sectionSubtitle}>
              Interactive demonstration of the reusable component library and application state primitives built on Arogya AI design tokens.
            </p>
          </div>

          <Card>
            <CardContent hasHeader={false}>
              <Tabs defaultValue="actions">
                <TabsList>
                  <TabsTrigger value="actions">Buttons &amp; Badges</TabsTrigger>
                  <TabsTrigger value="dialog">Dialog &amp; Forms</TabsTrigger>
                  <TabsTrigger value="feedback">Notifications &amp; Feedback</TabsTrigger>
                  <TabsTrigger value="states">Application States</TabsTrigger>
                </TabsList>

                {/* Tab 1: Buttons & Badges */}
                <TabsContent value="actions">
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", paddingTop: "var(--space-4)" }}>
                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        Button Variants &amp; Sizes
                      </h3>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)", alignItems: "center" }}>
                        <Button variant="primary" size="sm">Primary Small</Button>
                        <Button variant="primary" size="md">Primary Medium</Button>
                        <Button variant="secondary" size="md">Secondary</Button>
                        <Button variant="outline" size="md">Outline</Button>
                        <Button variant="ghost" size="md">Ghost</Button>
                        <Button variant="danger" size="md">Danger</Button>
                        <Button variant="primary" size="md" disabled>Disabled</Button>
                      </div>
                    </div>

                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        Status Badge Variants
                      </h3>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-3)", alignItems: "center" }}>
                        <Badge variant="neutral" withDot>Neutral Status</Badge>
                        <Badge variant="info" withDot>Research Evaluation</Badge>
                        <Badge variant="success" withDot>Verified Baseline</Badge>
                        <Badge variant="warning" withDot>Human Review Required</Badge>
                        <Badge variant="danger" withDot>Critical Threshold</Badge>
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* Tab 2: Dialog & Forms */}
                <TabsContent value="dialog">
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", paddingTop: "var(--space-4)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-4)", flexWrap: "wrap" }}>
                      <Dialog>
                        <DialogTrigger asChild>
                          <Button variant="outline">Open Research Dialog Preview</Button>
                        </DialogTrigger>
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>Research Parameter Confirmation</DialogTitle>
                            <DialogDescription>
                              Demonstration of the accessible modal dialog primitive with Escape key handling and backdrop focus trapping.
                            </DialogDescription>
                          </DialogHeader>
                          <DialogBody>
                            <FormField
                              label="Synthetic Cohort Filter"
                              htmlFor="demo-filter"
                              helperText="Enter synthetic cohort identifier or research study tag"
                            >
                              <Input id="demo-filter" placeholder="e.g., COHORT-SYNTH-2026" />
                            </FormField>
                            <div style={{ marginTop: "var(--space-4)" }}>
                              <Checkbox
                                id="demo-consent"
                                label="Acknowledge Research Prototype Constraints"
                                description="Confirms that outputs are for clinical evaluation only."
                                checked={consentChecked}
                                onChange={(e) => setConsentChecked(e.target.checked)}
                              />
                            </div>
                          </DialogBody>
                          <DialogFooter>
                            <DialogClose asChild>
                              <Button variant="secondary">Cancel</Button>
                            </DialogClose>
                            <DialogClose asChild>
                              <Button variant="primary">Confirm Parameters</Button>
                            </DialogClose>
                          </DialogFooter>
                        </DialogContent>
                      </Dialog>

                      <span style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)" }}>
                        Press the button to test accessible dialog opening, backdrop dismiss, and keyboard navigation.
                      </span>
                    </div>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "var(--space-4)" }}>
                      <FormField label="Sample Input (Standard)" htmlFor="sample-text" helperText="Standard text input field">
                        <Input id="sample-text" placeholder="Enter alphanumeric identifier" />
                      </FormField>

                      <FormField label="Sample Input (Invalid State)" htmlFor="sample-err" error="Value exceeds allowable synthetic range">
                        <Input id="sample-err" invalid defaultValue="INVALID_INPUT_99" />
                      </FormField>
                    </div>
                  </div>
                </TabsContent>

                {/* Tab 3: Notifications & Feedback */}
                <TabsContent value="feedback">
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", paddingTop: "var(--space-4)" }}>
                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        Accessible Notifications (Toast)
                      </h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
                        <Toast
                          title="Evaluation Protocol Loaded"
                          description="Synthetic evaluation benchmark ready for algorithmic comparison."
                          variant="info"
                        />
                        <Toast
                          title="Human Review Triggered"
                          description="Model entropy exceeded threshold; review flagged for qualified clinician."
                          variant="warning"
                        />
                      </div>
                    </div>

                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        Loading Placeholders (Skeleton)
                      </h3>
                      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)", maxWidth: "400px" }}>
                        <Skeleton height={20} width="60%" />
                        <Skeleton height={14} width="100%" />
                        <Skeleton height={14} width="85%" />
                      </div>
                    </div>
                  </div>
                </TabsContent>

                {/* Tab 4: Application States (Phase 4.5) */}
                <TabsContent value="states">
                  <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-6)", paddingTop: "var(--space-4)" }}>
                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        1. Reusable Loading State (Section Variant with Announcer)
                      </h3>
                      <LoadingState
                        variant="section"
                        label="Retrieving Longitudinal Laboratory Metrics..."
                        description="Accessing verified Module 3 observations repository."
                        lines={3}
                      />
                    </div>

                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        2. Reusable Empty State (Non-Diagnostic Query Notice)
                      </h3>
                      <EmptyState
                        preset="runs"
                        title="No Active Research Runs In Progress"
                        description="There are currently no inference pipelines or multi-agent evaluations executing against this synthetic cohort."
                        action={{
                          label: "Initiate Exploratory Run",
                          onClick: () => {},
                          variant: "primary",
                        }}
                        notice="Illustrative empty state demonstration — does not imply backend query execution."
                      />
                    </div>

                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        3. Reusable Error State with Safe Recovery Action
                      </h3>
                      {simulatedErrorResolved ? (
                        <div
                          style={{
                            padding: "var(--space-4)",
                            backgroundColor: "var(--color-success-bg)",
                            border: "1px solid var(--color-success-border)",
                            borderRadius: "var(--radius-md)",
                            color: "var(--color-success-fg)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                          }}
                        >
                          <span>Simulated recovery successful! State reset cleanly.</span>
                          <Button size="sm" variant="outline" onClick={() => setSimulatedErrorResolved(false)}>
                            Re-trigger Error Demo
                          </Button>
                        </div>
                      ) : (
                        <ErrorState
                          title="Simulated Pipeline Disconnection"
                          message="A non-fatal communication interruption occurred while contacting the synthetic evaluation service."
                          errorCode="ERR-SYNTH-EVAL-404"
                          onRetry={() => setSimulatedErrorResolved(true)}
                          retryLabel="Retry Connection"
                        />
                      )}
                    </div>

                    <div>
                      <h3 style={{ fontSize: "var(--font-size-body-sm)", color: "var(--color-text-muted)", textTransform: "uppercase", letterSpacing: "var(--letter-spacing-wider)", marginBottom: "var(--space-3)" }}>
                        4. Reusable Access-Denied State
                      </h3>
                      <AccessDeniedState
                        title="Restricted Governance Console"
                        message="Administrative controls are segregated to designated system oversight roles."
                        requiredRole="System Administrator"
                      />
                    </div>
                  </div>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </section>

        {/* Semantic Accessible Footer */}
        <footer className={styles.footer}>
          <div className={styles.footerInner}>
            <p className={styles.footerText}>
              Arogya AI &copy; 2026 — Clinical Multimodal Intelligence &amp; Decision-Support
              Prototype.
            </p>
            <p className={styles.footerNotice}>
              Academic research prototype. Designed strictly for clinician review and evaluation;
              not for autonomous medical decision-making.
            </p>
          </div>
        </footer>
      </div>
    </PageContainer>
  );
}
