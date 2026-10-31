import React, { forwardRef } from "react";
import styles from "./Skeleton.module.css";

export type SkeletonVariant = "rectangular" | "circular" | "text";

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: SkeletonVariant;
  width?: string | number;
  height?: string | number;
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  ({ variant = "rectangular", width, height, className = "", style, ...props }, ref) => {
    const variantClass = variant === "circular" ? styles.circular : variant === "text" ? styles.text : "";
    const combinedClassName = `${styles.skeleton} ${variantClass} ${className}`.trim();

    const inlineStyles: React.CSSProperties = {
      width: typeof width === "number" ? `${width}px` : width,
      height: typeof height === "number" ? `${height}px` : height,
      ...style,
    };

    return (
      <div
        ref={ref}
        aria-hidden="true"
        className={combinedClassName}
        style={inlineStyles}
        {...props}
      />
    );
  }
);

Skeleton.displayName = "Skeleton";
