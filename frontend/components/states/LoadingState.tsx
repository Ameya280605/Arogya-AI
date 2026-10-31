import React from "react";
import { Skeleton } from "@/components/ui";
import styles from "./LoadingState.module.css";

export interface LoadingStateProps {
  variant?: "page" | "section" | "card" | "inline";
  label?: string;
  description?: string;
  lines?: number;
  showSpinner?: boolean;
  className?: string;
  "aria-live"?: "polite" | "assertive" | "off";
}

export function LoadingState({
  variant = "section",
  label = "Loading content...",
  description,
  lines = 3,
  showSpinner = true,
  className = "",
  "aria-live": ariaLive = "polite",
}: LoadingStateProps) {
  const variantClass = {
    page: styles.pageVariant,
    section: styles.sectionVariant,
    card: styles.cardVariant,
    inline: styles.inlineVariant,
  }[variant];

  return (
    <div
      className={`${styles.loadingContainer} ${variantClass} ${className}`.trim()}
      role="status"
      aria-live={ariaLive}
      aria-label={label}
    >
      <div className={styles.statusMessage}>
        {showSpinner && <span className={styles.statusSpinner} aria-hidden="true" />}
        <span>{label}</span>
      </div>

      {description && <p className={styles.description}>{description}</p>}

      {/* Purely decorative visual placeholders */}
      <div className={styles.linesContainer} aria-hidden="true">
        {variant === "page" ? (
          <>
            <div className={styles.headerSkeleton}>
              <Skeleton width="40%" height={28} />
              <Skeleton width="70%" height={16} />
            </div>
            <div className={styles.gridSkeleton}>
              <Skeleton height={140} />
              <Skeleton height={140} />
              <Skeleton height={140} />
            </div>
          </>
        ) : (
          Array.from({ length: Math.max(1, lines) }).map((_, idx) => {
            const width = idx === 0 ? "85%" : idx === lines - 1 ? "60%" : "95%";
            return <Skeleton key={idx} width={width} height={18} />;
          })
        )}
      </div>

      <p className={styles.disclaimer} aria-hidden="true">
        Synthetic placeholder loading state — not connected to live patient or clinical data.
      </p>
    </div>
  );
}
