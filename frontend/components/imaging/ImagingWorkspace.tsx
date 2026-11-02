"use client";

import { useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { ErrorState } from "@/components/states/ErrorState";
import { LoginForm } from "@/components/auth/LoginForm";
import { Button } from "@/components/ui/Button";
import { fetchPatients, PatientsApiError } from "@/services/patients";
import {
  executeImagingAnalysis,
  fetchImagingHeatmap,
  fetchPatientImagingAssets,
  ImagingApiError,
} from "@/services/imaging";
import { useAuthToken } from "@/services/auth";
import type { Patient } from "@/types/patients";
import type {
  ImagingAnalysisRun,
  ImagingAsset,
  ImagingPrediction,
} from "@/types/imaging";
import styles from "./ImagingWorkspace.module.css";

const HEATMAP_LABELS = [
  "Atelectasis",
  "Consolidation",
  "Infiltration",
  "Pneumothorax",
  "Edema",
  "Emphysema",
  "Fibrosis",
  "Effusion",
  "Pneumonia",
  "Pleural_Thickening",
  "Cardiomegaly",
  "Nodule",
  "Mass",
  "Hernia",
];
const EMPTY_PATIENTS: Patient[] = [];

function isSupportedImage(asset: ImagingAsset): boolean {
  return (
    ["image/png", "image/jpeg"].includes(asset.media_type.toLowerCase()) &&
    /\.(png|jpe?g)$/i.test(asset.original_filename)
  );
}

function getStatusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function ImagingWorkspace() {
  const token = useAuthToken();
  const [patientLoadAttempt, setPatientLoadAttempt] = useState(0);
  const [patientLoad, setPatientLoad] = useState<{
    token: string;
    attempt: number;
    patients?: Patient[];
    error?: string;
  } | null>(null);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [assetLoadAttempt, setAssetLoadAttempt] = useState(0);
  const [assetLoad, setAssetLoad] = useState<{
    key: string;
    assets?: ImagingAsset[];
    error?: string;
  } | null>(null);
  const [selectedAssetId, setSelectedAssetId] = useState("");
  const [generateHeatmap, setGenerateHeatmap] = useState(true);
  const [heatmapLabel, setHeatmapLabel] = useState("Pneumonia");
  const [submitting, setSubmitting] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<ImagingAnalysisRun | null>(null);
  const [heatmapLoad, setHeatmapLoad] = useState<{
    runId: string;
    url?: string;
    error?: string;
  } | null>(null);

  const currentPatientLoad =
    token &&
    patientLoad?.token === token &&
    patientLoad.attempt === patientLoadAttempt
      ? patientLoad
      : null;
  const patients = currentPatientLoad?.patients ?? EMPTY_PATIENTS;
  const patientsLoading = Boolean(token && !currentPatientLoad);
  const patientsError = currentPatientLoad?.error ?? null;
  const assetLoadKey = `${token ?? ""}:${selectedPatientId}:${assetLoadAttempt}`;
  const currentAssetLoad =
    assetLoad?.key === assetLoadKey ? assetLoad : null;
  const assets = currentAssetLoad?.assets ?? [];
  const assetsLoading = Boolean(token && selectedPatientId && !currentAssetLoad);
  const assetsError = currentAssetLoad?.error ?? null;

  useEffect(() => {
    if (!token) return;

    const activeToken = token;
    const controller = new AbortController();
    let cancelled = false;
    async function loadPatients() {
      const firstPage = await fetchPatients({
        page: 1,
        page_size: 100,
        signal: controller.signal,
      });
      const pageCount = Math.ceil(firstPage.total / 100);
      const remainingPages = await Promise.all(
        Array.from({ length: Math.max(0, pageCount - 1) }, (_, index) =>
          fetchPatients({
            page: index + 2,
            page_size: 100,
            signal: controller.signal,
          })
        )
      );
      if (!cancelled) {
        setPatientLoad({
          token: activeToken,
          attempt: patientLoadAttempt,
          patients: [
            ...firstPage.items,
            ...remainingPages.flatMap((page) => page.items),
          ],
        });
      }
    }

    loadPatients()
      .catch((error: unknown) => {
        if (
          cancelled ||
          (error instanceof Error && error.name === "AbortError")
        ) return;
        const message =
          error instanceof PatientsApiError || error instanceof Error
            ? error.message
            : "Unable to load patients.";
        setPatientLoad({
          token: activeToken,
          attempt: patientLoadAttempt,
          error: message,
        });
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [patientLoadAttempt, token]);

  useEffect(() => {
    if (!token || !selectedPatientId) return;

    const controller = new AbortController();
    let cancelled = false;
    fetchPatientImagingAssets(selectedPatientId, controller.signal)
      .then((patientAssets) => {
        if (!cancelled) {
          setAssetLoad({
            key: assetLoadKey,
            assets: patientAssets.filter(isSupportedImage),
          });
        }
      })
      .catch((error: unknown) => {
        if (
          cancelled ||
          (error instanceof Error && error.name === "AbortError")
        ) return;
        const message =
          error instanceof ImagingApiError || error instanceof Error
            ? error.message
            : "Unable to load this patient's uploaded images.";
        setAssetLoad({ key: assetLoadKey, error: message });
      });

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [assetLoadAttempt, assetLoadKey, selectedPatientId, token]);

  const gradcam = analysis?.results_summary?.gradcam;

  useEffect(() => {
    if (!analysis || !gradcam) return;

    const controller = new AbortController();
    let objectUrl: string | null = null;
    fetchImagingHeatmap(analysis.id, controller.signal)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setHeatmapLoad({ runId: analysis.id, url: objectUrl });
      })
      .catch((error: unknown) => {
        if (error instanceof Error && error.name === "AbortError") return;
        setHeatmapLoad({
          runId: analysis.id,
          error:
            error instanceof Error
              ? error.message
              : "The Grad-CAM image could not be loaded.",
        });
      });

    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [analysis, gradcam]);

  const currentHeatmapLoad =
    analysis && heatmapLoad?.runId === analysis.id ? heatmapLoad : null;
  const heatmapUrl = currentHeatmapLoad?.url ?? null;
  const heatmapError = currentHeatmapLoad?.error ?? null;
  const heatmapLoading = Boolean(analysis && gradcam && !currentHeatmapLoad);

  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.id === selectedPatientId) ?? null,
    [patients, selectedPatientId]
  );
  const predictions: ImagingPrediction[] =
    analysis?.results_summary?.predictions ?? [];

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedPatientId || !selectedAssetId) return;

    setSubmitting(true);
    setRequestError(null);
    setAnalysis(null);

    try {
      const result = await executeImagingAnalysis(selectedPatientId, {
        asset_id: selectedAssetId,
        generate_heatmap: generateHeatmap,
        heatmap_label: heatmapLabel,
      });
      setAnalysis(result);
    } catch (error: unknown) {
      setRequestError(
        error instanceof Error ? error.message : "Imaging analysis failed."
      );
    } finally {
      setSubmitting(false);
    }
  }

  function handlePatientChange(patientId: string) {
    setSelectedPatientId(patientId);
    setSelectedAssetId("");
    setAnalysis(null);
    setRequestError(null);
  }

  function handleAssetChange(assetId: string) {
    setSelectedAssetId(assetId);
    setAnalysis(null);
    setRequestError(null);
  }

  if (!token) {
    return (
      <div className={styles.workspace}>
        <p className={styles.disclaimer} role="note">
          Research use only. Model scores are not calibrated probabilities and
          are not a diagnosis or a guide to treatment.
        </p>
        <LoginForm
          title="Sign in to analyze imaging"
          description="An authenticated account with analysis and patient-read permissions is required."
          redirectUrl="/imaging"
        />
      </div>
    );
  }

  return (
    <div className={styles.workspace}>
      <p className={styles.disclaimer} role="note">
        <strong>Research use only.</strong> Model scores are not calibrated
        probabilities and must not be used as a diagnosis or to guide
        treatment. Findings require independent qualified clinical review.
      </p>

      <section className={styles.card} aria-labelledby="imaging-form-heading">
        <div className={styles.cardHeader}>
          <div>
            <h2 id="imaging-form-heading">Analyze an uploaded chest X-ray</h2>
            <p>Select a patient and a previously uploaded PNG or JPEG image.</p>
          </div>
          <span className={styles.researchTag}>Research workflow</span>
        </div>

        {patientsError ? (
          <ErrorState
            title="Patients could not be loaded"
            message={patientsError}
            onRetry={() => setPatientLoadAttempt((attempt) => attempt + 1)}
          />
        ) : (
          <form className={styles.form} onSubmit={handleSubmit}>
            <label className={styles.field}>
              <span>Patient</span>
              <select
                value={selectedPatientId}
                onChange={(event) => handlePatientChange(event.target.value)}
                disabled={patientsLoading || submitting}
                required
              >
                <option value="">
                  {patientsLoading ? "Loading patients…" : "Select a patient"}
                </option>
                {patients.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.mrn_pseudonym}
                  </option>
                ))}
              </select>
              {currentPatientLoad && patients.length === 0 && (
                <span className={styles.emptyMessage} role="status">
                  No patients are available to analyze for this account.
                </span>
              )}
            </label>

            {selectedPatientId && (
              <label className={styles.field}>
                <span>Uploaded chest X-ray</span>
                <select
                  value={selectedAssetId}
                  onChange={(event) => handleAssetChange(event.target.value)}
                  disabled={assetsLoading || submitting || assets.length === 0}
                  required
                >
                  <option value="">
                    {assetsLoading
                      ? "Loading uploaded images…"
                      : assets.length
                        ? "Select an image"
                        : "No supported PNG or JPEG images"}
                  </option>
                  {assets.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      {asset.original_filename} · {asset.media_type}
                    </option>
                  ))}
                </select>
                {assetsError && <span role="alert">{assetsError}</span>}
              </label>
            )}
            {assetsError && (
              <Button
                type="button"
                variant="outline"
                onClick={() => setAssetLoadAttempt((attempt) => attempt + 1)}
              >
                Retry loading images
              </Button>
            )}

            <label className={styles.checkboxField}>
              <input
                type="checkbox"
                checked={generateHeatmap}
                onChange={(event) => setGenerateHeatmap(event.target.checked)}
                disabled={submitting}
              />
              Generate a Grad-CAM heatmap
            </label>

            {generateHeatmap && (
              <label className={styles.field}>
                <span>Heatmap finding</span>
                <select
                  value={heatmapLabel}
                  onChange={(event) => setHeatmapLabel(event.target.value)}
                  disabled={submitting}
                >
                  {HEATMAP_LABELS.map((label) => (
                    <option key={label} value={label}>
                      {label.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </label>
            )}

            {requestError && <p className={styles.error} role="alert">{requestError}</p>}

            <Button
              type="submit"
              disabled={
                patientsLoading ||
                assetsLoading ||
                submitting ||
                !selectedPatientId ||
                !selectedAssetId
              }
            >
              {submitting ? "Analyzing image…" : "Run imaging analysis"}
            </Button>
          </form>
        )}
      </section>

      {analysis && (
        <section className={styles.card} aria-labelledby="imaging-results-heading">
          <div className={styles.resultHeader}>
            <div>
              <h2 id="imaging-results-heading">Analysis results</h2>
              <p>
                {selectedPatient?.mrn_pseudonym ?? "Selected patient"} · Run{" "}
                <code>{analysis.id}</code>
              </p>
            </div>
            <span className={`${styles.status} ${styles[`status_${analysis.status}`] ?? ""}`}>
              {getStatusLabel(analysis.status)}
            </span>
          </div>

          {analysis.error_message && (
            <p className={styles.error} role="alert">{analysis.error_message}</p>
          )}

          {predictions.length > 0 && (
            <>
              <p className={styles.scoreNote}>
                Raw model scores (not calibrated probabilities)
              </p>
              <div className={styles.tableWrap}>
                <table className={styles.predictionTable}>
                  <thead>
                    <tr>
                      <th scope="col">Finding</th>
                      <th scope="col">Raw score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {predictions.map((prediction) => (
                      <tr key={prediction.label}>
                        <th scope="row">{prediction.label.replaceAll("_", " ")}</th>
                        <td>{prediction.score.toFixed(4)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {analysis.status === "completed" && predictions.length === 0 && (
            <p className={styles.emptyMessage} role="status">
              No prediction scores were returned for this analysis.
            </p>
          )}

          {gradcam && (
            <div className={styles.heatmapSection}>
              <h3>Grad-CAM · {gradcam.label.replaceAll("_", " ")}</h3>
              <p>{gradcam.note}</p>
              {heatmapLoading && <p role="status">Loading heatmap…</p>}
              {heatmapError && <p className={styles.error} role="alert">{heatmapError}</p>}
              {heatmapUrl && (
                <Image
                  className={styles.heatmap}
                  src={heatmapUrl}
                  alt={`Research-only Grad-CAM overlay for ${gradcam.label.replaceAll("_", " ")}`}
                  width={1024}
                  height={1024}
                  unoptimized
                />
              )}
            </div>
          )}

          <p className={styles.resultsDisclaimer}>
            {analysis.results_summary?.disclaimer ??
              "Research use only. These results are not a diagnosis or treatment recommendation."}
          </p>
        </section>
      )}
    </div>
  );
}
