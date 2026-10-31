import React from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Label, Select } from "@/components/ui/Form";
import type { AnalysisRunStatus } from "@/types/dashboard";
import styles from "./DashboardFilterBar.module.css";

export interface DashboardFilterState {
  /** UTC ISO Start date filter in YYYY-MM-DD format (or empty string) */
  startDate: string;
  /** UTC ISO End date filter in YYYY-MM-DD format (or empty string) */
  endDate: string;
  /** Analysis run status filter */
  status: AnalysisRunStatus | "all";
}

export const DEFAULT_FILTER_STATE: DashboardFilterState = {
  startDate: "",
  endDate: "",
  status: "all",
};

export interface DashboardFilterBarProps {
  /** Active filter state */
  filters: DashboardFilterState;
  /** Callback fired whenever any filter field changes */
  onFilterChange: (newFilters: DashboardFilterState) => void;
  /** Callback fired to reset all filters to default state */
  onReset: () => void;
  /** Disabled state (e.g. while loading or unavailable) */
  disabled?: boolean;
  /** Provenance statement explaining filter scope */
  provenance?: string;
  /** Optional custom CSS class name */
  className?: string;
}

/**
 * Reusable, accessible filter bar for the Overview Dashboard.
 *
 * Provides date-range and analysis-status filtering controls that dynamically update
 * candidate review runs, recent activity feeds, and distribution charts.
 */
export function DashboardFilterBar({
  filters,
  onFilterChange,
  onReset,
  disabled = false,
  provenance = "Filters apply dynamically to synthetic seed records (Module 3)",
  className = "",
}: DashboardFilterBarProps) {
  // Validate date range boundaries
  const hasInvalidRange = Boolean(
    filters.startDate &&
    filters.endDate &&
    filters.startDate > filters.endDate
  );

  // Compute count of active non-default filters
  let activeFilterCount = 0;
  if (filters.startDate) activeFilterCount++;
  if (filters.endDate) activeFilterCount++;
  if (filters.status !== "all") activeFilterCount++;

  const handleStartDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      startDate: e.target.value,
    });
  };

  const handleEndDateChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filters,
      endDate: e.target.value,
    });
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onFilterChange({
      ...filters,
      status: e.target.value as AnalysisRunStatus | "all",
    });
  };

  return (
    <section
      className={`${styles.filterContainer} ${className}`.trim()}
      aria-labelledby="dashboard-filters-heading"
      role="search"
    >
      <div className={styles.headerRow}>
        <div className={styles.titleArea}>
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          <h2 id="dashboard-filters-heading" className={styles.filterTitle}>
            Dashboard Filters
          </h2>
          <Badge variant={activeFilterCount > 0 ? "info" : "neutral"} size="sm">
            {activeFilterCount > 0 ? `${activeFilterCount} Active` : "All Records"}
          </Badge>
        </div>

        <div className={styles.actionsGroup}>
          <Button
            variant="outline"
            size="sm"
            onClick={onReset}
            disabled={disabled || activeFilterCount === 0}
            aria-label="Reset all dashboard filters"
          >
            Reset Filters
          </Button>
        </div>
      </div>

      {hasInvalidRange && (
        <div className={styles.validationNotice} role="alert">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>
            Invalid date range: Start date ({filters.startDate}) must precede or equal end date ({filters.endDate}).
          </span>
        </div>
      )}

      <div className={styles.controlsRow}>
        {/* 1. Start Date Filter */}
        <div className={styles.filterGroup}>
          <Label htmlFor="filter-start-date" className={styles.filterLabel}>
            Start Date (UTC)
          </Label>
          <Input
            id="filter-start-date"
            type="date"
            value={filters.startDate}
            onChange={handleStartDateChange}
            disabled={disabled}
            invalid={hasInvalidRange}
            aria-invalid={hasInvalidRange ? "true" : undefined}
          />
        </div>

        {/* 2. End Date Filter */}
        <div className={styles.filterGroup}>
          <Label htmlFor="filter-end-date" className={styles.filterLabel}>
            End Date (UTC)
          </Label>
          <Input
            id="filter-end-date"
            type="date"
            value={filters.endDate}
            onChange={handleEndDateChange}
            disabled={disabled}
            invalid={hasInvalidRange}
            aria-invalid={hasInvalidRange ? "true" : undefined}
          />
        </div>

        {/* 3. Analysis Lifecycle Status Filter */}
        <div className={styles.filterGroup}>
          <Label htmlFor="filter-analysis-status" className={styles.filterLabel}>
            Analysis Status
          </Label>
          <Select
            id="filter-analysis-status"
            value={filters.status}
            onChange={handleStatusChange}
            disabled={disabled}
            aria-label="Filter records by AI model analysis status"
          >
            <option value="all">All Statuses (Full Cohort)</option>
            <option value="completed">Completed</option>
            <option value="running">Running</option>
            <option value="abstained">Abstained (Safety Flag)</option>
            <option value="queued">Queued</option>
            <option value="failed">Failed</option>
          </Select>
        </div>
      </div>

      <div className={styles.provenanceFooter}>
        <span>Provenance: {provenance}</span>
        <span>Scope: Date &amp; status criteria refine review candidates, activities, and charts</span>
      </div>
    </section>
  );
}
