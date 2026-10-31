import React from "react";
import { Button } from "@/components/ui";
import styles from "./ErrorState.module.css";

export interface ErrorStateProps {
  title?: string;
  message: string;
  errorCode?: string;
  errorId?: string;
  onRetry?: () => void;
  retryLabel?: string;
  secondaryAction?: React.ReactNode;
  variant?: "card" | "callout";
  headingLevel?: "h2" | "h3" | "h4";
  className?: string;
}

export function ErrorState({
  title = "An error occurred",
  message,
  errorCode,
  errorId,
  onRetry,
  retryLabel = "Try again",
  secondaryAction,
  variant = "card",
  headingLevel = "h3",
  className = "",
}: ErrorStateProps) {
  const HeadingTag = headingLevel;

  return (
    <div
      className={`${styles.errorContainer} ${variant === "callout" ? styles.calloutVariant : ""} ${className}`.trim()}
      role="alert"
    >
      <div className={styles.iconWrapper} aria-hidden="true">
        <svg
          width="24"
          height="24"
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

      <HeadingTag className={styles.title}>{title}</HeadingTag>
      <p className={styles.message}>{message}</p>

      {(errorCode || errorId) && (
        <div className={styles.diagnosticBox} aria-label="Diagnostic reference">
          <span>Diagnostic ID:</span>
          <code>{errorCode || errorId}</code>
        </div>
      )}

      {(onRetry || secondaryAction) && (
        <div className={styles.actionsContainer}>
          {onRetry && (
            <Button variant="danger" size="md" onClick={onRetry}>
              {retryLabel}
            </Button>
          )}
          {secondaryAction}
        </div>
      )}
    </div>
  );
}

export interface InlineErrorProps {
  message: string;
  id?: string;
  className?: string;
}

export function InlineError({ message, id, className = "" }: InlineErrorProps) {
  return (
    <div
      id={id}
      className={`${styles.inlineError} ${className}`.trim()}
      role="alert"
    >
      <svg
        className={styles.inlineIcon}
        width="14"
        height="14"
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
      <span>{message}</span>
    </div>
  );
}
