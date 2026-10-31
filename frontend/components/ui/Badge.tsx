import React, { forwardRef } from "react";
import styles from "./Badge.module.css";

export type BadgeVariant = "neutral" | "info" | "success" | "warning" | "danger";
export type BadgeSize = "sm" | "md";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
  withDot?: boolean;
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      children,
      className = "",
      variant = "neutral",
      size = "md",
      withDot = false,
      ...props
    },
    ref
  ) => {
    const variantClass = styles[variant] || styles.neutral;
    const sizeClass = styles[size] || styles.md;
    const combinedClassName = `${styles.badge} ${variantClass} ${sizeClass} ${className}`.trim();

    return (
      <span ref={ref} className={combinedClassName} {...props}>
        {withDot && <span className={styles.dot} aria-hidden="true" />}
        <span>{children}</span>
      </span>
    );
  }
);

Badge.displayName = "Badge";
