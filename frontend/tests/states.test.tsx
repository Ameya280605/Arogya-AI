import { describe, it } from "node:test";
import assert from "node:assert";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import {
  LoadingState,
  EmptyState,
  ErrorState,
  InlineError,
  AccessDeniedState,
  PlannedFeatureState,
} from "../components/states";
import NotFound from "../app/not-found";

describe("LoadingState Component", () => {
  it("renders with role='status' and accessible aria-live", () => {
    const html = renderToStaticMarkup(
      <LoadingState
        variant="section"
        label="Loading research observations..."
        description="Retrieving observation entities from database"
      />
    );

    assert.ok(html.includes('role="status"'));
    assert.ok(html.includes('aria-live="polite"'));
    assert.ok(html.includes('aria-label="Loading research observations..."'));
    assert.ok(html.includes("Loading research observations..."));
    assert.ok(html.includes("Retrieving observation entities from database"));
    assert.ok(html.includes('aria-hidden="true"'));
    assert.ok(html.includes("Synthetic placeholder loading state"));
  });

  it("supports page variant with grid layout", () => {
    const html = renderToStaticMarkup(
      <LoadingState variant="page" label="Preparing platform overview..." />
    );

    assert.ok(html.includes("pageVariant"));
    assert.ok(html.includes("headerSkeleton"));
    assert.ok(html.includes("gridSkeleton"));
  });

  it("supports card and inline variants", () => {
    const htmlCard = renderToStaticMarkup(<LoadingState variant="card" />);
    assert.ok(htmlCard.includes("cardVariant"));

    const htmlInline = renderToStaticMarkup(<LoadingState variant="inline" showSpinner={false} />);
    assert.ok(htmlInline.includes("inlineVariant"));
    assert.ok(!htmlInline.includes("statusSpinner"));
  });
});

describe("EmptyState Component", () => {
  it("renders title, description, and semantic region role", () => {
    const html = renderToStaticMarkup(
      <EmptyState
        title="No Cohorts Found"
        description="No synthetic cohorts match the selected filter criteria."
      />
    );

    assert.ok(html.includes('role="region"'));
    assert.ok(html.includes('aria-label="No Cohorts Found"'));
    assert.ok(html.includes("No Cohorts Found"));
    assert.ok(html.includes("No synthetic cohorts match the selected filter criteria."));
  });

  it("supports presets and rendered icons", () => {
    const htmlSearch = renderToStaticMarkup(
      <EmptyState
        preset="search"
        title="No Search Results"
        description="Try adjusting query parameters."
      />
    );
    assert.ok(htmlSearch.includes("<svg"));

    const htmlRuns = renderToStaticMarkup(
      <EmptyState
        preset="runs"
        title="No Research Runs"
        description="Inference bench is idle."
      />
    );
    assert.ok(htmlRuns.includes("<polyline"));
  });

  it("renders primary action when action config is supplied", () => {
    const html = renderToStaticMarkup(
      <EmptyState
        title="Empty Workspace"
        description="Initialize a new study."
        action={{
          label: "Create Synthetic Case",
          onClick: () => {},
          variant: "primary",
        }}
        notice="Illustrative empty state demonstration"
      />
    );

    assert.ok(html.includes("Create Synthetic Case"));
    assert.ok(html.includes("<button"));
    assert.ok(html.includes("Illustrative empty state demonstration"));
  });
});

describe("ErrorState & InlineError Components", () => {
  it("renders with role='alert' and accessible heading", () => {
    const html = renderToStaticMarkup(
      <ErrorState
        title="Inference Connection Failed"
        message="Unable to establish communication with the synthetic evaluation runner."
      />
    );

    assert.ok(html.includes('role="alert"'));
    assert.ok(html.includes("Inference Connection Failed"));
    assert.ok(html.includes("Unable to establish communication with the synthetic evaluation runner."));
    // When onRetry is not provided, retry button is NOT rendered
    assert.ok(!html.includes("Try again"));
  });

  it("renders retry button only when onRetry callback is provided", () => {
    let retried = false;
    const html = renderToStaticMarkup(
      <ErrorState
        message="Transient service failure"
        onRetry={() => {
          retried = true;
        }}
        retryLabel="Attempt Reconnection"
      />
    );

    assert.ok(html.includes("Attempt Reconnection"));
    assert.ok(html.includes("<button"));
    assert.strictEqual(retried, false);
  });

  it("renders diagnostic code when provided without exposing sensitive stacks", () => {
    const html = renderToStaticMarkup(
      <ErrorState
        message="Safe diagnostic summary"
        errorCode="ERR-CODE-503-PERSISTENCE"
      />
    );

    assert.ok(html.includes("Diagnostic ID:"));
    assert.ok(html.includes("<code>ERR-CODE-503-PERSISTENCE</code>"));
  });

  it("renders InlineError with alert role", () => {
    const html = renderToStaticMarkup(
      <InlineError id="error-field" message="Required field missing" />
    );

    assert.ok(html.includes('id="error-field"'));
    assert.ok(html.includes('role="alert"'));
    assert.ok(html.includes("Required field missing"));
  });
});

describe("AccessDeniedState Component", () => {
  it("renders access restricted messaging without exposing sensitive secrets", () => {
    const html = renderToStaticMarkup(
      <AccessDeniedState
        title="Access Restricted"
        message="You do not have clearance for administrative governance controls."
        requiredRole="Platform Administrator"
      />
    );

    assert.ok(html.includes('role="region"'));
    assert.ok(html.includes("Access Restricted"));
    assert.ok(html.includes("You do not have clearance for administrative governance controls."));
    assert.ok(html.includes("Required Authorization:"));
    assert.ok(html.includes("Platform Administrator"));
    assert.ok(html.includes("Presentation layer only."));
    assert.ok(html.includes("Return to Overview"));
  });
});

describe("PlannedFeatureState Component", () => {
  it("renders honest roadmap status, target block, and verified foundations", () => {
    const html = renderToStaticMarkup(
      <PlannedFeatureState
        moduleName="Module 6: Patient Intelligence"
        targetBlock="Block 2: Clinical Domain Foundation"
        statusText="Planned for a future module"
        description="Patient Intelligence is scheduled for full implementation in Module 6."
        verifiedFoundations={[
          "SQLAlchemy Models: Patient, Encounter, Observation (Module 3)",
          "Alembic Migrations: Seed data verified",
        ]}
      />
    );

    assert.ok(html.includes('role="region"'));
    assert.ok(html.includes("Module 6: Patient Intelligence"));
    assert.ok(html.includes("Block 2: Clinical Domain Foundation"));
    assert.ok(html.includes("Planned for a future module"));
    assert.ok(html.includes("Shell Active"));
    assert.ok(html.includes("SQLAlchemy Models: Patient, Encounter, Observation (Module 3)"));
    assert.ok(html.includes("Research prototype notice:"));
  });
});

describe("Route-Level Not-Found Component", () => {
  it("renders 404 EmptyState with navigation action to Overview", () => {
    const html = renderToStaticMarkup(<NotFound />);

    assert.ok(html.includes("Page Not Found (404)"));
    assert.ok(html.includes("Return to Overview"));
    assert.ok(html.includes('href="/"'));
  });
});
