import React from "react";
import { Badge, type BadgeVariant, type BadgeSize } from "@/components/ui/Badge";
import type { AnalysisRunStatus } from "@/types/dashboard";

export interface AnalysisStatusIndicatorProps {
  /**
   * The lifecycle status string of an analysis run.
   * Can be one of the canonical values ('queued', 'running', 'completed', 'failed', 'abstained')
   * or any non-standard/future string handled defensively.
   */
  status?: AnalysisRunStatus | string | null;
  /** Size of the rendered badge ('sm' or 'md') */
  size?: BadgeSize;
  /** Whether to display a status dot indicator */
  withDot?: boolean;
  /** Optional custom CSS class name */
  className?: string;
}

interface StatusMetadata {
  label: string;
  variant: BadgeVariant;
  description: string;
}

/**
 * Mapping of canonical analysis run statuses to clinical design tokens and descriptive labels.
 *
 * NOTE: Lifecycle status reflects technical pipeline execution state only.
 * It does not imply clinical correctness, diagnostic accuracy, or safety clearance.
 */
const STATUS_METADATA: Record<AnalysisRunStatus, StatusMetadata> = {
  completed: {
    label: "Completed",
    variant: "success",
    description: "Inference pipeline successfully concluded with research findings",
  },
  running: {
    label: "Running",
    variant: "info",
    description: "Actively executing inference pipeline",
  },
  queued: {
    label: "Queued",
    variant: "neutral",
    description: "Awaiting compute worker allocation",
  },
  abstained: {
    label: "Abstained (Safety Flag)",
    variant: "warning",
    description: "Model triggered automated abstention due to high entropy, uncertainty, or safety filters",
  },
  failed: {
    label: "Failed",
    variant: "danger",
    description: "Execution terminated abnormally due to runtime error",
  },
};

/**
 * Reusable analysis-run status indicator component.
 *
 * Implements accessible, color-independent status presentation using design tokens.
 * Handles unknown or future statuses defensively without crashing or falsely implying success.
 */
export function AnalysisStatusIndicator({
  status,
  size = "sm",
  withDot = true,
  className = "",
}: AnalysisStatusIndicatorProps) {
  const normalizedKey = (status || "").toLowerCase().trim() as AnalysisRunStatus;
  const config = STATUS_METADATA[normalizedKey];

  if (!config) {
    // Defensive handling: Unrecognized, future, or missing status
    const displayLabel = status && status.trim().length > 0
      ? `Unknown (${status.trim()})`
      : "Unknown Status";

    return (
      <Badge
        variant="neutral"
        size={size}
        withDot={withDot}
        className={className}
        aria-label={`Analysis status: ${displayLabel}`}
        title="Unrecognized or non-standard execution status (technical lifecycle indicator only)"
      >
        {displayLabel}
      </Badge>
    );
  }

  return (
    <Badge
      variant={config.variant}
      size={size}
      withDot={withDot}
      className={className}
      aria-label={`Analysis status: ${config.label}`}
      title={`${config.description} (technical lifecycle indicator only; not diagnostic validation)`}
    >
      {config.label}
    </Badge>
  );
}
