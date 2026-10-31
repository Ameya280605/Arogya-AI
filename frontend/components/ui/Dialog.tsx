"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useId,
  forwardRef,
} from "react";
import styles from "./Dialog.module.css";

interface DialogContextValue {
  isOpen: boolean;
  openDialog: () => void;
  closeDialog: () => void;
  titleId: string;
  descriptionId: string;
}

const DialogContext = createContext<DialogContextValue | null>(null);

function useDialogContext() {
  const context = useContext(DialogContext);
  if (!context) {
    throw new Error("Dialog components must be used within a <Dialog> provider");
  }
  return context;
}

/* -----------------------------------------------------------------------------
   Dialog Root Provider
   ----------------------------------------------------------------------------- */
export interface DialogProps {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  defaultOpen?: boolean;
  children: React.ReactNode;
}

export function Dialog({
  open: controlledOpen,
  onOpenChange,
  defaultOpen = false,
  children,
}: DialogProps) {
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen);
  const isControlled = controlledOpen !== undefined;
  const isOpen = isControlled ? controlledOpen : uncontrolledOpen;

  const titleId = useId();
  const descriptionId = useId();

  const openDialog = () => {
    if (!isControlled) setUncontrolledOpen(true);
    onOpenChange?.(true);
  };

  const closeDialog = () => {
    if (!isControlled) setUncontrolledOpen(false);
    onOpenChange?.(false);
  };

  return (
    <DialogContext.Provider
      value={{
        isOpen,
        openDialog,
        closeDialog,
        titleId,
        descriptionId,
      }}
    >
      {children}
    </DialogContext.Provider>
  );
}

/* -----------------------------------------------------------------------------
   Dialog Trigger
   ----------------------------------------------------------------------------- */
export interface DialogTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
}

export const DialogTrigger = forwardRef<HTMLButtonElement, DialogTriggerProps>(
  ({ onClick, asChild = false, children, ...props }, ref) => {
    const { openDialog } = useDialogContext();

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      onClick?.(e);
      if (!e.defaultPrevented) {
        openDialog();
      }
    };

    if (asChild && React.isValidElement(children)) {
      const child = children as React.ReactElement<{ onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void }>;
      return React.cloneElement(child, {
        onClick: (e: React.MouseEvent<HTMLButtonElement>) => {
          child.props?.onClick?.(e);
          handleClick(e);
        },
      });
    }

    return (
      <button ref={ref} type="button" onClick={handleClick} {...props}>
        {children}
      </button>
    );
  }
);

DialogTrigger.displayName = "DialogTrigger";

/* -----------------------------------------------------------------------------
   Dialog Content (Modal & Backdrop)
   ----------------------------------------------------------------------------- */
export interface DialogContentProps extends React.HTMLAttributes<HTMLDivElement> {
  showCloseButton?: boolean;
}

export const DialogContent = forwardRef<HTMLDivElement, DialogContentProps>(
  ({ showCloseButton = true, className = "", children, ...props }, ref) => {
    const { isOpen, closeDialog, titleId, descriptionId } = useDialogContext();
    const contentRef = useRef<HTMLDivElement | null>(null);
    const previouslyFocusedElement = useRef<HTMLElement | null>(null);

    // Escape key listener & focus management
    useEffect(() => {
      if (!isOpen) return;

      if (typeof document !== "undefined") {
        previouslyFocusedElement.current = document.activeElement as HTMLElement | null;
      }

      const handleKeyDown = (event: KeyboardEvent) => {
        if (event.key === "Escape") {
          event.preventDefault();
          closeDialog();
          return;
        }

        // Tab focus containment
        if (event.key === "Tab" && contentRef.current) {
          const focusableSelectors = [
            'a[href]',
            'button:not([disabled])',
            'textarea:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
          ].join(", ");

          const focusableElements = Array.from(
            contentRef.current.querySelectorAll<HTMLElement>(focusableSelectors)
          );

          if (focusableElements.length === 0) {
            event.preventDefault();
            return;
          }

          const firstElement = focusableElements[0];
          const lastElement = focusableElements[focusableElements.length - 1];

          if (event.shiftKey) {
            if (
              document.activeElement === firstElement ||
              document.activeElement === contentRef.current
            ) {
              event.preventDefault();
              lastElement.focus();
            }
          } else {
            if (document.activeElement === lastElement) {
              event.preventDefault();
              firstElement.focus();
            }
          }
        }
      };

      window.addEventListener("keydown", handleKeyDown);
      return () => {
        window.removeEventListener("keydown", handleKeyDown);
        if (previouslyFocusedElement.current && typeof previouslyFocusedElement.current.focus === "function") {
          previouslyFocusedElement.current.focus();
        }
      };
    }, [isOpen, closeDialog]);

    // Focus on open
    useEffect(() => {
      if (isOpen && contentRef.current) {
        contentRef.current.focus();
      }
    }, [isOpen]);

    if (!isOpen) {
      return null;
    }

    const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) {
        closeDialog();
      }
    };

    return (
      <div className={styles.backdrop} onClick={handleBackdropClick} role="presentation">
        <div
          ref={(node) => {
            contentRef.current = node;
            if (typeof ref === "function") ref(node);
            else if (ref) ref.current = node;
          }}
          role="dialog"
          aria-modal="true"
          aria-labelledby={titleId}
          aria-describedby={descriptionId}
          tabIndex={-1}
          className={`${styles.content} ${className}`.trim()}
          {...props}
        >
          {showCloseButton && (
            <button
              type="button"
              className={styles.closeButton}
              onClick={closeDialog}
              aria-label="Close dialog"
            >
              <svg
                width="18"
                height="18"
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
          {children}
        </div>
      </div>
    );
  }
);

DialogContent.displayName = "DialogContent";

/* -----------------------------------------------------------------------------
   Dialog Header
   ----------------------------------------------------------------------------- */
export type DialogHeaderProps = React.HTMLAttributes<HTMLDivElement>;

export const DialogHeader = forwardRef<HTMLDivElement, DialogHeaderProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <div ref={ref} className={`${styles.header} ${className}`.trim()} {...props}>
        {children}
      </div>
    );
  }
);

DialogHeader.displayName = "DialogHeader";

/* -----------------------------------------------------------------------------
   Dialog Title
   ----------------------------------------------------------------------------- */
export interface DialogTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  as?: "h1" | "h2" | "h3" | "h4";
}

export const DialogTitle = forwardRef<HTMLHeadingElement, DialogTitleProps>(
  ({ as = "h2", className = "", children, ...props }, ref) => {
    const { titleId } = useDialogContext();
    const Component = as;

    return (
      <Component id={titleId} ref={ref} className={`${styles.title} ${className}`.trim()} {...props}>
        {children}
      </Component>
    );
  }
);

DialogTitle.displayName = "DialogTitle";

/* -----------------------------------------------------------------------------
   Dialog Description
   ----------------------------------------------------------------------------- */
export type DialogDescriptionProps = React.HTMLAttributes<HTMLParagraphElement>;

export const DialogDescription = forwardRef<HTMLParagraphElement, DialogDescriptionProps>(
  ({ className = "", children, ...props }, ref) => {
    const { descriptionId } = useDialogContext();

    return (
      <p id={descriptionId} ref={ref} className={`${styles.description} ${className}`.trim()} {...props}>
        {children}
      </p>
    );
  }
);

DialogDescription.displayName = "DialogDescription";

/* -----------------------------------------------------------------------------
   Dialog Body
   ----------------------------------------------------------------------------- */
export type DialogBodyProps = React.HTMLAttributes<HTMLDivElement>;

export const DialogBody = forwardRef<HTMLDivElement, DialogBodyProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <div ref={ref} className={`${styles.body} ${className}`.trim()} {...props}>
        {children}
      </div>
    );
  }
);

DialogBody.displayName = "DialogBody";

/* -----------------------------------------------------------------------------
   Dialog Footer
   ----------------------------------------------------------------------------- */
export type DialogFooterProps = React.HTMLAttributes<HTMLDivElement>;

export const DialogFooter = forwardRef<HTMLDivElement, DialogFooterProps>(
  ({ className = "", children, ...props }, ref) => {
    return (
      <div ref={ref} className={`${styles.footer} ${className}`.trim()} {...props}>
        {children}
      </div>
    );
  }
);

DialogFooter.displayName = "DialogFooter";

/* -----------------------------------------------------------------------------
   Dialog Close
   ----------------------------------------------------------------------------- */
export interface DialogCloseProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  asChild?: boolean;
}

export const DialogClose = forwardRef<HTMLButtonElement, DialogCloseProps>(
  ({ onClick, asChild = false, children, ...props }, ref) => {
    const { closeDialog } = useDialogContext();

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      onClick?.(e);
      if (!e.defaultPrevented) {
        closeDialog();
      }
    };

    if (asChild && React.isValidElement(children)) {
      const child = children as React.ReactElement<{ onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void }>;
      return React.cloneElement(child, {
        onClick: (e: React.MouseEvent<HTMLButtonElement>) => {
          child.props?.onClick?.(e);
          handleClick(e);
        },
      });
    }

    return (
      <button ref={ref} type="button" onClick={handleClick} {...props}>
        {children}
      </button>
    );
  }
);

DialogClose.displayName = "DialogClose";
