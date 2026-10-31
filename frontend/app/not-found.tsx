import React from "react";
import Link from "next/link";
import { EmptyState } from "@/components/states";
import { Button } from "@/components/ui";

export default function NotFound() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "65vh",
        padding: "var(--space-8) var(--space-4)",
      }}
    >
      <div style={{ maxWidth: "540px", width: "100%" }}>
        <EmptyState
          preset="search"
          title="Page Not Found (404)"
          description="The requested route, study parameter, or view could not be located in this Arogya AI prototype build."
          action={
            <Button variant="primary" size="md" asChild>
              <Link href="/">Return to Overview</Link>
            </Button>
          }
          notice="If you navigated here via a planned roadmap link, check the specifications on the Overview page."
        />
      </div>
    </div>
  );
}
