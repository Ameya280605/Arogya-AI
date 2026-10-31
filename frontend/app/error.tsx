"use client";

import React, { useEffect } from "react";
import Link from "next/link";
import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error securely on client side for diagnostic evaluation
    console.error("Route Error Boundary caught error:", error);
  }, [error]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        padding: "var(--space-8) var(--space-4)",
      }}
    >
      <div style={{ maxWidth: "560px", width: "100%" }}>
        <ErrorState
          title="Interface Error Encountered"
          message="An unexpected exception occurred while rendering this view. You may attempt to recover the state by clicking retry below."
          errorId={error.digest ? `DIGEST-${error.digest.slice(0, 8)}` : undefined}
          onRetry={reset}
          retryLabel="Reload Component"
          secondaryAction={
            <Button variant="outline" size="md" asChild>
              <Link href="/">Back to Overview</Link>
            </Button>
          }
        />
      </div>
    </div>
  );
}
