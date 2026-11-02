import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  executeImagingAnalysis,
  fetchImagingHeatmap,
  fetchPatientImagingAssets,
  ImagingApiError,
} from "../services/imaging";

describe("Imaging API client", () => {
  it("loads assets for the selected patient", async (context) => {
    let requestedUrl = "";
    context.mock.method(globalThis, "fetch", async (input: RequestInfo | URL) => {
      requestedUrl = String(input);
      return new Response("[]", {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const assets = await fetchPatientImagingAssets("patient / 1");

    assert.deepEqual(assets, []);
    assert.ok(requestedUrl.endsWith("/patients/patient%20%2F%201/assets"));
  });

  it("submits an imaging request with the selected asset", async (context) => {
    let requestedUrl = "";
    let requestedBody = "";
    context.mock.method(
      globalThis,
      "fetch",
      async (input: RequestInfo | URL, init?: RequestInit) => {
        requestedUrl = String(input);
        requestedBody = String(init?.body);
        return new Response(
          JSON.stringify({
            id: "run-id",
            patient_id: "patient-id",
            asset_id: "asset-id",
            model_name: "cxr_densenet121_nih",
            model_version: "densenet121-res224-nih",
            status: "completed",
            results_summary: { predictions: [] },
            created_at: "2026-01-01T00:00:00Z",
          }),
          { status: 201, headers: { "Content-Type": "application/json" } }
        );
      }
    );

    const result = await executeImagingAnalysis("patient-id", {
      asset_id: "asset-id",
      generate_heatmap: true,
      heatmap_label: "Pneumonia",
    });

    assert.ok(requestedUrl.endsWith("/patients/patient-id/analysis/imaging"));
    assert.deepEqual(JSON.parse(requestedBody), {
      asset_id: "asset-id",
      generate_heatmap: true,
      heatmap_label: "Pneumonia",
    });
    assert.equal(result.status, "completed");
  });

  it("retrieves a heatmap blob and reports API failures", async (context) => {
    context.mock.method(globalThis, "fetch", async () =>
      new Response(new Uint8Array([137, 80, 78, 71]), {
        status: 200,
        headers: { "Content-Type": "image/png" },
      })
    );

    const heatmap = await fetchImagingHeatmap("run-id");
    assert.equal(heatmap.type, "image/png");

    context.mock.restoreAll();
    context.mock.method(globalThis, "fetch", async () =>
      new Response(JSON.stringify({ detail: "No heatmap available." }), {
        status: 404,
        headers: { "Content-Type": "application/json" },
      })
    );

    await assert.rejects(
      fetchImagingHeatmap("missing-run"),
      (error: unknown) =>
        error instanceof ImagingApiError &&
        error.status === 404 &&
        error.message.includes("404")
    );
  });
});
