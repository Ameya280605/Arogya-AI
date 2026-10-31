import React from "react";
import { Badge } from "@/components/ui";
import styles from "./PlannedFeatureState.module.css";

export interface PlannedFeatureStateProps {
  moduleName: string;
  targetBlock: string;
  statusText?: string;
  description: string;
  verifiedFoundations?: string[];
  action?: React.ReactNode;
  headingLevel?: "h2" | "h3" | "h4";
  className?: string;
}

export function PlannedFeatureState({
  moduleName,
  targetBlock,
  statusText = "Planned for a future module",
  description,
  verifiedFoundations = [],
  action,
  headingLevel = "h2",
  className = "",
}: PlannedFeatureStateProps) {
  const HeadingTag = headingLevel;

  return (
    <section
      className={`${styles.container} ${className}`.trim()}
      role="region"
      aria-label={`${moduleName} Status`}
    >
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <span className={styles.targetBlock}>{targetBlock}</span>
          <HeadingTag className={styles.title}>{moduleName}</HeadingTag>
        </div>
        <div className={styles.statusBadges}>
          <Badge variant="warning" withDot>
            {statusText}
          </Badge>
          <Badge variant="info">Shell Active</Badge>
        </div>
      </div>

      <p className={styles.description}>{description}</p>

      {verifiedFoundations.length > 0 && (
        <div className={styles.foundationsBox}>
          <h3 className={styles.foundationsTitle}>Verified Architecture Foundations</h3>
          <ul className={styles.foundationsList}>
            {verifiedFoundations.map((foundation, idx) => (
              <li key={idx} className={styles.foundationItem}>
                <svg
                  className={styles.checkIcon}
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span>{foundation}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {action && <div className={styles.actionsArea}>{action}</div>}

      <p className={styles.disclaimerNotice}>
        Research prototype notice: Interactive workflows, clinical inference pipelines, and live EHR
        integrations are not active in this frontend shell.
      </p>
    </section>
  );
}
