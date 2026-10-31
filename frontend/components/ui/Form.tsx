import React, { forwardRef, useId } from "react";
import styles from "./Form.module.css";

/* -----------------------------------------------------------------------------
   Label
   ----------------------------------------------------------------------------- */
export interface LabelProps extends React.LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
}

export const Label = forwardRef<HTMLLabelElement, LabelProps>(
  ({ required = false, className = "", children, ...props }, ref) => {
    return (
      <label ref={ref} className={`${styles.label} ${className}`.trim()} {...props}>
        <span>{children}</span>
        {required && (
          <span className={styles.requiredStar} aria-hidden="true">
            *
          </span>
        )}
      </label>
    );
  }
);

Label.displayName = "Label";

/* -----------------------------------------------------------------------------
   Input
   ----------------------------------------------------------------------------- */
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
  sizeVariant?: "sm" | "md";
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ invalid = false, sizeVariant = "md", className = "", ...props }, ref) => {
    const sizeClass = sizeVariant === "sm" ? styles.inputSm : "";
    const invalidClass = invalid ? styles.invalid : "";
    const combinedClassName = `${styles.input} ${sizeClass} ${invalidClass} ${className}`.trim();

    return (
      <input
        ref={ref}
        aria-invalid={invalid ? "true" : undefined}
        className={combinedClassName}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";

/* -----------------------------------------------------------------------------
   Textarea
   ----------------------------------------------------------------------------- */
export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ invalid = false, className = "", ...props }, ref) => {
    const invalidClass = invalid ? styles.invalid : "";
    const combinedClassName = `${styles.textarea} ${invalidClass} ${className}`.trim();

    return (
      <textarea
        ref={ref}
        aria-invalid={invalid ? "true" : undefined}
        className={combinedClassName}
        {...props}
      />
    );
  }
);

Textarea.displayName = "Textarea";

/* -----------------------------------------------------------------------------
   Select
   ----------------------------------------------------------------------------- */
export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ invalid = false, className = "", children, ...props }, ref) => {
    const invalidClass = invalid ? styles.invalid : "";
    const combinedClassName = `${styles.select} ${invalidClass} ${className}`.trim();

    return (
      <select
        ref={ref}
        aria-invalid={invalid ? "true" : undefined}
        className={combinedClassName}
        {...props}
      >
        {children}
      </select>
    );
  }
);

Select.displayName = "Select";

/* -----------------------------------------------------------------------------
   Checkbox
   ----------------------------------------------------------------------------- */
export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "type"> {
  label: React.ReactNode;
  description?: React.ReactNode;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, description, disabled = false, className = "", id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id || generatedId;

    return (
      <label
        htmlFor={inputId}
        className={`${styles.checkboxContainer} ${disabled ? styles.checkboxContainerDisabled : ""} ${className}`.trim()}
      >
        <input
          ref={ref}
          id={inputId}
          type="checkbox"
          disabled={disabled}
          className={styles.checkboxInput}
          {...props}
        />
        <span className={styles.checkboxCustom} aria-hidden="true">
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <div>
          <span className={styles.checkboxLabelText}>{label}</span>
          {description && <p className={styles.checkboxDescription}>{description}</p>}
        </div>
      </label>
    );
  }
);

Checkbox.displayName = "Checkbox";

/* -----------------------------------------------------------------------------
   FormField (Wrapper with Label, Error, and Helper text)
   ----------------------------------------------------------------------------- */
export interface FormFieldProps extends React.HTMLAttributes<HTMLDivElement> {
  label?: string;
  required?: boolean;
  htmlFor?: string;
  error?: string;
  helperText?: string;
}

export const FormField = forwardRef<HTMLDivElement, FormFieldProps>(
  ({ label, required = false, htmlFor, error, helperText, className = "", children, ...props }, ref) => {
    const errorId = htmlFor ? `${htmlFor}-error` : undefined;
    const helperId = htmlFor ? `${htmlFor}-helper` : undefined;

    return (
      <div ref={ref} className={`${styles.formField} ${className}`.trim()} {...props}>
        {label && (
          <Label htmlFor={htmlFor} required={required}>
            {label}
          </Label>
        )}
        {children}
        {error && (
          <span id={errorId} className={styles.errorText} role="alert">
            <svg
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
            <span>{error}</span>
          </span>
        )}
        {!error && helperText && (
          <span id={helperId} className={styles.helperText}>
            {helperText}
          </span>
        )}
      </div>
    );
  }
);

FormField.displayName = "FormField";
