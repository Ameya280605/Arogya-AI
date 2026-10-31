import React, { forwardRef } from "react";
import styles from "./Toast.module.css";

export type ToastVariant = "neutral" | "info" | "success" | "warning" | "danger";

export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  title?: string;
  description?: string;
  variant?: ToastVariant;
  onClose?: () => void;
  icon?: React.ReactNode;
}

export const Toast = forwardRef<HTMLDivElement, ToastProps>(
  (
    {
      title,
      description,
      variant = "neutral",
      onClose,
      icon,
      className = "",
      children,
      ...props
    },
    ref
  ) => {
    const isAlert = variant === "danger" || variant === "warning";
    const variantClass = styles[variant] || styles.neutral;
    const combinedClassName = `${styles.toast} ${variantClass} ${className}`.trim();

    return (
      <div
        ref={ref}
        role={isAlert ? "alert" : "status"}
        aria-live={isAlert ? "assertive" : "polite"}
        className={combinedClassName}
        {...props}
      >
        {icon && (
          <span className={styles.icon} aria-hidden="true">
            {icon}
          </span>
        )}
        <div className={styles.content}>
          {title && <h4 className={styles.title}>{title}</h4>}
          {description && <p className={styles.description}>{description}</p>}
          {children}
        </div>
        {onClose && (
          <button
            type="button"
            className={styles.closeButton}
            onClick={onClose}
            aria-label="Dismiss notification"
          >
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
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>
    );
  }
);

Toast.displayName = "Toast";
