import React, { forwardRef } from "react";
import styles from "./Card.module.css";

/* -----------------------------------------------------------------------------
   Card Root
   ----------------------------------------------------------------------------- */
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  as?: "article" | "div" | "section";
  interactive?: boolean;
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ as = "div", interactive = false, className = "", children, ...props }, ref) => {
    const Component = as;
    const combinedClassName = `${styles.card} ${interactive ? styles.cardInteractive : ""} ${className}`.trim();

    return (
      <Component ref={ref as React.Ref<HTMLDivElement & HTMLElement>} className={combinedClassName} {...props}>
        {children}
      </Component>
    );
  }
);

Card.displayName = "Card";

/* -----------------------------------------------------------------------------
   Card Header
   ----------------------------------------------------------------------------- */
export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;

export const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <div ref={ref} className={`${styles.cardHeader} ${className}`.trim()} {...props}>
        {children}
      </div>
    );
  }
);

CardHeader.displayName = "CardHeader";

/* -----------------------------------------------------------------------------
   Card Title
   ----------------------------------------------------------------------------- */
export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  as?: "h1" | "h2" | "h3" | "h4" | "h5" | "h6";
}

export const CardTitle = forwardRef<HTMLHeadingElement, CardTitleProps>(
  ({ as = "h3", className = "", children, ...props }, ref) => {
    const Component = as;
    return (
      <Component ref={ref} className={`${styles.cardTitle} ${className}`.trim()} {...props}>
        {children}
      </Component>
    );
  }
);

CardTitle.displayName = "CardTitle";

/* -----------------------------------------------------------------------------
   Card Description
   ----------------------------------------------------------------------------- */
export type CardDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

export const CardDescription = forwardRef<HTMLParagraphElement, CardDescriptionProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <p ref={ref} className={`${styles.cardDescription} ${className}`.trim()} {...props}>
        {children}
      </p>
    );
  }
);

CardDescription.displayName = "CardDescription";

/* -----------------------------------------------------------------------------
   Card Content
   ----------------------------------------------------------------------------- */
export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  hasHeader?: boolean;
}

export const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ hasHeader = true, className = "", children, ...props }, ref) => {
    const combinedClassName = `${styles.cardContent} ${!hasHeader ? styles.cardContentNoHeader : ""} ${className}`.trim();

    return (
      <div ref={ref} className={combinedClassName} {...props}>
        {children}
      </div>
    );
  }
);

CardContent.displayName = "CardContent";

/* -----------------------------------------------------------------------------
   Card Footer
   ----------------------------------------------------------------------------- */
export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>;

export const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <div ref={ref} className={`${styles.cardFooter} ${className}`.trim()} {...props}>
        {children}
      </div>
    );
  }
);

CardFooter.displayName = "CardFooter";
