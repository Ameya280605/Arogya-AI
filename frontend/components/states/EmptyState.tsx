import React from "react";
import { Button, ButtonProps } from "@/components/ui";
import styles from "./EmptyState.module.css";

export type EmptyStatePreset = "records" | "search" | "runs" | "filter" | "generic";

export interface EmptyStateActionConfig {
  label: string;
  onClick?: () => void;
  variant?: ButtonProps["variant"];
  disabled?: boolean;
}

export interface EmptyStateProps {
  title: string;
  description: string;
  preset?: EmptyStatePreset;
  icon?: React.ReactNode;
  action?: EmptyStateActionConfig | React.ReactNode;
  secondaryAction?: React.ReactNode;
  headingLevel?: "h2" | "h3" | "h4";
  variant?: "dashed" | "subtle";
  notice?: string;
  className?: string;
}

function getDefaultIcon(preset: EmptyStatePreset) {
  switch (preset) {
    case "search":
      return (
        <svg
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
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      );
    case "runs":
      return (
        <svg
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
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
        </svg>
      );
    case "filter":
      return (
        <svg
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
          <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
        </svg>
      );
    case "records":
    case "generic":
    default:
      return (
        <svg
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
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="15" y2="15" />
        </svg>
      );
  }
}

export function EmptyState({
  title,
  description,
  preset = "records",
  icon,
  action,
  secondaryAction,
  headingLevel = "h3",
  variant = "dashed",
  notice,
  className = "",
}: EmptyStateProps) {
  const HeadingTag = headingLevel;
  const renderedIcon = icon ?? getDefaultIcon(preset);

  const isActionConfig = (act: unknown): act is EmptyStateActionConfig => {
    return typeof act === "object" && act !== null && "label" in act && !React.isValidElement(act);
  };

  return (
    <div
      className={`${styles.emptyContainer} ${variant === "subtle" ? styles.subtle : ""} ${className}`.trim()}
      role="region"
      aria-label={title}
    >
      <div className={styles.iconWrapper} aria-hidden="true">
        {renderedIcon}
      </div>

      <HeadingTag className={styles.title}>{title}</HeadingTag>
      <p className={styles.description}>{description}</p>

      {(action || secondaryAction) && (
        <div className={styles.actionsContainer}>
          {action &&
            (isActionConfig(action) ? (
              <Button
                variant={action.variant ?? "primary"}
                onClick={action.onClick}
                disabled={action.disabled}
              >
                {action.label}
              </Button>
            ) : (
              (action as React.ReactNode)
            ))}
          {secondaryAction}
        </div>
      )}

      {notice && <p className={styles.contextNotice}>{notice}</p>}
    </div>
  );
}
