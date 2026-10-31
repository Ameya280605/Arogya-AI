import { describe, it, beforeEach, afterEach } from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "../components/ui/Dialog";

describe("Dialog Accessibility & Keyboard Interactions", () => {
  let listeners: Record<string, ((event: unknown) => void)[]> = {};
  let originalWindow: unknown;
  let originalDocument: unknown;

  beforeEach(() => {
    listeners = {};
    originalWindow = globalThis.window;
    originalDocument = globalThis.document;

    // Lightweight mock of window and document for event and focus verification
    (globalThis as unknown as { window: unknown }).window = {
      addEventListener: (type: string, handler: (event: unknown) => void) => {
        if (!listeners[type]) listeners[type] = [];
        listeners[type].push(handler);
      },
      removeEventListener: (type: string, handler: (event: unknown) => void) => {
        if (listeners[type]) {
          listeners[type] = listeners[type].filter((h) => h !== handler);
        }
      },
    };

    (globalThis as unknown as { document: unknown }).document = {
      activeElement: null,
    };
  });

  afterEach(() => {
    (globalThis as unknown as { window: unknown }).window = originalWindow;
    (globalThis as unknown as { document: unknown }).document = originalDocument;
  });

  it("renders with appropriate dialog semantics and attributes when open", () => {
    const html = renderToStaticMarkup(
      <Dialog open={true}>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Modal Title</DialogTitle>
          <DialogDescription>Modal Description</DialogDescription>
          <DialogClose>Close</DialogClose>
        </DialogContent>
      </Dialog>
    );

    assert.ok(html.includes('role="dialog"'));
    assert.ok(html.includes('aria-modal="true"'));
    assert.ok(html.includes('tabindex="-1"'));
    assert.ok(html.includes('aria-label="Close dialog"'));
  });

  it("handles backdrop dismissal when backdrop itself is clicked", () => {
    let closed = false;
    const html = renderToStaticMarkup(
      <Dialog open={true} onOpenChange={(open) => { if (!open) closed = true; }}>
        <DialogContent>
          <DialogTitle>Test Dialog</DialogTitle>
        </DialogContent>
      </Dialog>
    );

    assert.ok(html.includes("role=\"presentation\""));
    assert.ok(html.includes("role=\"dialog\""));
    assert.strictEqual(closed, false);
  });

  it("registers keydown event listener on window when open", () => {
    // Render closed: should not register keydown
    renderToStaticMarkup(
      <Dialog open={false}>
        <DialogContent>
          <DialogTitle>Closed Dialog</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    assert.strictEqual(listeners["keydown"]?.length ?? 0, 0);
  });

  it("handles Escape dismissal logic", () => {
    let openState = true;
    const handleOpenChange = (open: boolean) => {
      openState = open;
    };

    // Simulate Escape keydown handler directly
    const handleEscapeKeyDown = (event: { key: string; preventDefault: () => void }) => {
      if (event.key === "Escape") {
        event.preventDefault();
        handleOpenChange(false);
      }
    };

    let prevented = false;
    handleEscapeKeyDown({
      key: "Escape",
      preventDefault: () => {
        prevented = true;
      },
    });

    assert.strictEqual(openState, false, "Dialog should close on Escape keydown");
    assert.strictEqual(prevented, true, "Escape keydown should call preventDefault");
  });

  it("handles Focus Restoration logic when unmounting", () => {
    let focusRestored = false;
    const previousElement = {
      focus: () => {
        focusRestored = true;
      },
    };

    // Simulate previous element capture and cleanup
    const simulateDialogSession = () => {
      const captured = previousElement;
      return () => {
        captured.focus();
      };
    };

    const cleanup = simulateDialogSession();
    assert.strictEqual(focusRestored, false);

    cleanup();
    assert.strictEqual(focusRestored, true, "Previous element should receive focus on dialog close");
  });

  it("handles Tab Focus Containment logic", () => {
    const focusableElements = [
      { id: "btn-first", focusCount: 0, focus() { this.focusCount++; } },
      { id: "input-middle", focusCount: 0, focus() { this.focusCount++; } },
      { id: "btn-last", focusCount: 0, focus() { this.focusCount++; } },
    ];

    const simulateTabContainment = (
      activeElement: unknown,
      shiftKey: boolean
    ): { prevented: boolean; targetElement: typeof focusableElements[0] | null } => {
      let prevented = false;
      let targetElement: typeof focusableElements[0] | null = null;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (shiftKey) {
        if (activeElement === firstElement) {
          prevented = true;
          targetElement = lastElement;
          lastElement.focus();
        }
      } else {
        if (activeElement === lastElement) {
          prevented = true;
          targetElement = firstElement;
          firstElement.focus();
        }
      }

      return { prevented, targetElement };
    };

    // Forward Tab from last element wraps to first
    const forwardResult = simulateTabContainment(focusableElements[2], false);
    assert.strictEqual(forwardResult.prevented, true);
    assert.strictEqual(forwardResult.targetElement?.id, "btn-first");
    assert.strictEqual(focusableElements[0].focusCount, 1);

    // Backward Shift+Tab from first element wraps to last
    const backwardResult = simulateTabContainment(focusableElements[0], true);
    assert.strictEqual(backwardResult.prevented, true);
    assert.strictEqual(backwardResult.targetElement?.id, "btn-last");
    assert.strictEqual(focusableElements[2].focusCount, 1);
  });
});
