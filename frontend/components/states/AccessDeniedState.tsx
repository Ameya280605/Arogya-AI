import React from "react";
import Link from "next/link";
import { Button } from "@/components/ui";
import styles from "./AccessDeniedState.module.css";

export interface AccessDeniedStateProps {
  title?: string;
  message?: string;
  requiredRole?: string;
  action?: React.ReactNode;
  headingLevel?: "h2" | "h3" | "h4";
  className?: string;
}

export function AccessDeniedState({
  title = "Access Restricted",
  message = "You do not have administrative clearance or permission to access this domain.",
  requiredRole,
  action,
  headingLevel = "h3",
  className = "",
}: AccessDeniedStateProps) {
  const HeadingTag = headingLevel;

  return (
    <div
      className={`${styles.accessContainer} ${className}`.trim()}
      role="region"
      aria-label={title}
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
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
      </div>

      <HeadingTag className={styles.title}>{title}</HeadingTag>
      <p className={styles.message}>{message}</p>

      {requiredRole && (
        <div className={styles.roleNotice}>
          <span>Required Authorization:</span>
          <strong>{requiredRole}</strong>
        </div>
      )}

      <div className={styles.actionsContainer}>
        {action ?? (
          <Button variant="outline" size="md" asChild>
            <Link href="/">Return to Overview</Link>
          </Button>
        )}
      </div>

      <p className={styles.boundaryNotice}>
        Presentation layer only. Security boundaries, authentication, and authorization policies
        are strictly enforced by backend services and cryptographically signed sessions.
      </p>
    </div>
  );
}
