import React, { forwardRef } from "react";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";
export type ButtonSize = "sm" | "md" | "lg";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  leadingIcon?: React.ReactNode;
  trailingIcon?: React.ReactNode;
  asChild?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className = "",
      variant = "primary",
      size = "md",
      leadingIcon,
      trailingIcon,
      disabled = false,
      type = "button",
      asChild = false,
      ...props
    },
    ref
  ) => {
    const variantClass = styles[variant] || styles.primary;
    const sizeClass = styles[size] || styles.md;
    const combinedClassName = `${styles.button} ${variantClass} ${sizeClass} ${className}`.trim();

    if (asChild && React.isValidElement(children)) {
      const child = children as React.ReactElement<{ className?: string }>;
      return React.cloneElement(child, {
        className: `${combinedClassName} ${child.props?.className || ""}`.trim(),
        ...props,
      });
    }

    return (
      <button
        ref={ref}
        type={type}
        className={combinedClassName}
        disabled={disabled}
        aria-disabled={disabled ? "true" : undefined}
        {...props}
      >
        {leadingIcon && (
          <span className={styles.icon} aria-hidden="true">
            {leadingIcon}
          </span>
        )}
        {children && <span>{children}</span>}
        {trailingIcon && (
          <span className={styles.icon} aria-hidden="true">
            {trailingIcon}
          </span>
        )}
      </button>
    );
  }
);

Button.displayName = "Button";
