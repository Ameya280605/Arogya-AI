import React from "react";
import { Breadcrumbs, BreadcrumbItem } from "./Breadcrumbs";
import styles from "./PageContainer.module.css";

export interface PageContainerProps {
  title: string;
  description?: string;
  breadcrumbs?: BreadcrumbItem[];
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
}

export function PageContainer({
  title,
  description,
  breadcrumbs,
  badge,
  actions,
  children,
}: PageContainerProps) {
  return (
    <div className={styles.pageContainer}>
      <header className={styles.pageHeader}>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <Breadcrumbs items={breadcrumbs} />
        )}
        <div className={styles.titleRow}>
          <div>
            <h1 className={styles.pageTitle}>{title}</h1>
            {description && (
              <p className={styles.pageDescription}>{description}</p>
            )}
          </div>
          {(badge || actions) && (
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              {badge}
              {actions}
            </div>
          )}
        </div>
      </header>

      <div className={styles.pageBody}>{children}</div>
    </div>
  );
}
