"use client";

import { useEffect, useMemo, useState } from "react";
import { LoginForm } from "@/components/auth/LoginForm";
import { AccessDeniedState } from "@/components/states/AccessDeniedState";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Button } from "@/components/ui/Button";
import { fetchPatients, PatientsApiError } from "@/services/patients";
import {
  ClinicalWorkspaceApiError,
  createCaseAnalysis,
  createClinicalCase,
  downloadCaseAttachment,
  fetchPatientCases,
  removeCaseAttachment,
  reviewCaseAnalysis,
  retryCaseAnalysis,
  submitCaseAnalysis,
  updateClinicalCase,
  uploadCaseAttachment,
} from "@/services/clinicalWorkspace";
import { useAuthToken } from "@/services/auth";
import type { Patient } from "@/types/patients";
import type {
  CaseAnalysisPayload,
  ClinicalAnalysisRun,
  ClinicalCase,
  ClinicalCasePayload,
  ClinicalMeasurement,
} from "@/types/clinicalWorkspace";
import styles from "./ClinicalWorkspace.module.css";

interface MeasurementDraft {
  kind: "vital" | "laboratory";
  code: string;
  display_name: string;
  numeric_value: string;
  unit: string;
  reference_low: string;
  reference_high: string;
}

interface CaseForm {
  symptoms: string;
  symptom_duration: string;
  medical_history: string;
  medications: string;
  allergies: string;
  clinical_notes: string;
  measurements: MeasurementDraft[];
}

const EMPTY_FORM: CaseForm = {
  symptoms: "",
  symptom_duration: "",
  medical_history: "",
  medications: "",
  allergies: "",
  clinical_notes: "",
  measurements: [
    { kind: "vital", code: "temperature", display_name: "Temperature", numeric_value: "", unit: "°C", reference_low: "", reference_high: "" },
    { kind: "vital", code: "8480-6", display_name: "Systolic blood pressure", numeric_value: "", unit: "mmHg", reference_low: "", reference_high: "" },
    { kind: "vital", code: "8462-4", display_name: "Diastolic blood pressure", numeric_value: "", unit: "mmHg", reference_low: "", reference_high: "" },
    { kind: "vital", code: "8867-4", display_name: "Heart rate", numeric_value: "", unit: "bpm", reference_low: "", reference_high: "" },
    { kind: "vital", code: "9279-1", display_name: "Respiratory rate", numeric_value: "", unit: "breaths/min", reference_low: "", reference_high: "" },
    { kind: "vital", code: "2708-6", display_name: "SpO₂", numeric_value: "", unit: "%", reference_low: "", reference_high: "" },
    { kind: "vital", code: "height", display_name: "Height", numeric_value: "", unit: "cm", reference_low: "", reference_high: "" },
    { kind: "vital", code: "weight", display_name: "Weight", numeric_value: "", unit: "kg", reference_low: "", reference_high: "" },
  ],
};
const EMPTY_PATIENTS: Patient[] = [];
const EMPTY_CASES: ClinicalCase[] = [];

function splitLines(value: string): string[] {
  return value.split(/\r?\n/).map((part) => part.trim()).filter(Boolean);
}

function toForm(clinicalCase: ClinicalCase): CaseForm {
  const measurements = clinicalCase.observations.map((observation) => {
    const metadata = observation.source_metadata ?? {};
    return {
      kind: metadata.kind === "laboratory" ? "laboratory" as const : "vital" as const,
      code: observation.code,
      display_name: observation.display_name,
      numeric_value: observation.numeric_value === null ? "" : String(observation.numeric_value),
      unit: observation.unit ?? "",
      reference_low: typeof metadata.reference_low === "number" ? String(metadata.reference_low) : "",
      reference_high: typeof metadata.reference_high === "number" ? String(metadata.reference_high) : "",
    };
  });
  return {
    symptoms: clinicalCase.symptoms ?? "",
    symptom_duration: clinicalCase.symptom_duration ?? "",
    medical_history: clinicalCase.medical_history ?? "",
    medications: clinicalCase.medications.join("\n"),
    allergies: clinicalCase.allergies.join("\n"),
    clinical_notes: clinicalCase.clinical_notes ?? "",
    measurements: measurements.length ? measurements : EMPTY_FORM.measurements.map((item) => ({ ...item })),
  };
}

function toPayload(form: CaseForm): ClinicalCasePayload {
  const measurements: ClinicalMeasurement[] = form.measurements
    .filter((item) => item.numeric_value.trim() !== "")
    .map((item) => ({
      kind: item.kind,
      code: item.code.trim(),
      display_name: item.display_name.trim(),
      numeric_value: Number(item.numeric_value),
      unit: item.unit.trim() || null,
      reference_low: item.reference_low.trim() ? Number(item.reference_low) : null,
      reference_high: item.reference_high.trim() ? Number(item.reference_high) : null,
    }));
  return {
    symptoms: form.symptoms,
    symptom_duration: form.symptom_duration,
    medical_history: form.medical_history,
    medications: splitLines(form.medications),
    allergies: splitLines(form.allergies),
    clinical_notes: form.clinical_notes,
    measurements,
  };
}

function messageOf(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "The request could not be completed.";
}

function displayRunStatus(run: ClinicalAnalysisRun): string {
  return run.status.replaceAll("_", " ");
}

function tabularDraftInput(
  values: { age: string; gender: string; smoking: string; imaginary_min: string; imaginary_avg: string; real_min: string; real_avg: string },
): NonNullable<CaseAnalysisPayload["tabular_input"]> {
  const input: NonNullable<CaseAnalysisPayload["tabular_input"]> = {};
  if (values.age.trim()) input.age = Number(values.age);
  if (values.gender.trim()) input.gender = Number(values.gender);
  if (values.smoking.trim()) input.smoking = Number(values.smoking);
  if (values.imaginary_min.trim()) input.imaginary_min = Number(values.imaginary_min);
  if (values.imaginary_avg.trim()) input.imaginary_avg = Number(values.imaginary_avg);
  if (values.real_min.trim()) input.real_min = Number(values.real_min);
  if (values.real_avg.trim()) input.real_avg = Number(values.real_avg);
  return input;
}

export function ClinicalWorkspace() {
  const token = useAuthToken();
  const [patientLoad, setPatientLoad] = useState<{ token: string; patients?: Patient[]; error?: string; denied?: boolean } | null>(null);
  const [selectedPatientId, setSelectedPatientId] = useState("");
  const [caseLoad, setCaseLoad] = useState<{ patientId: string; cases?: ClinicalCase[]; error?: string; denied?: boolean } | null>(null);
  const [selectedCase, setSelectedCase] = useState<ClinicalCase | null>(null);
  const [form, setForm] = useState<CaseForm>(EMPTY_FORM);
  const [isSaving, setIsSaving] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [attachmentBusy, setAttachmentBusy] = useState(false);
  const [analysisType, setAnalysisType] = useState<"tabular" | "imaging">("imaging");
  const [selectedImageId, setSelectedImageId] = useState("");
  const [tabular, setTabular] = useState({ age: "", gender: "", smoking: "1", imaginary_min: "", imaginary_avg: "", real_min: "", real_avg: "" });

  const patientLoadCurrent = token && patientLoad?.token === token ? patientLoad : null;
  const patients = patientLoadCurrent?.patients ?? EMPTY_PATIENTS;
  const currentCaseLoad = caseLoad?.patientId === selectedPatientId ? caseLoad : null;
  const cases = currentCaseLoad?.cases ?? EMPTY_CASES;
  const loadingPatients = Boolean(token && !patientLoadCurrent);
  const loadingCases = Boolean(selectedPatientId && !currentCaseLoad);
  const selectedPatient = useMemo(
    () => patients.find((patient) => patient.id === selectedPatientId) ?? null,
    [patients, selectedPatientId],
  );
  const isReadOnly = selectedCase?.status === "completed" || selectedCase?.status === "cancelled";

  useEffect(() => {
    if (!token) return;
    const controller = new AbortController();
    const activeToken = token;
    async function loadPatients() {
      const firstPage = await fetchPatients({ page: 1, page_size: 100, signal: controller.signal });
      const remainingPages = await Promise.all(
        Array.from({ length: Math.max(0, Math.ceil(firstPage.total / 100) - 1) }, (_, index) =>
          fetchPatients({ page: index + 2, page_size: 100, signal: controller.signal }),
        ),
      );
      return [...firstPage.items, ...remainingPages.flatMap((page) => page.items)];
    }

    loadPatients()
      .then((items) => {
        if (controller.signal.aborted) return;
        setPatientLoad({ token: activeToken, patients: items });
        setSelectedPatientId((current) => current || items[0]?.id || "");
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setPatientLoad({
          token: activeToken,
          error: messageOf(error),
          denied: error instanceof PatientsApiError && [401, 403].includes(error.status),
        });
      });
    return () => controller.abort();
  }, [token]);

  useEffect(() => {
    if (!token || !selectedPatientId) {
      return;
    }
    const controller = new AbortController();
    const patientId = selectedPatientId;
    fetchPatientCases(patientId, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setCaseLoad({ patientId, cases: result });
        setSelectedCase(result[0] ?? null);
        setForm(result[0] ? toForm(result[0]) : EMPTY_FORM);
        setSelectedImageId(
          result[0]?.attachments.find((asset) =>
            ["image/png", "image/jpeg"].includes(asset.media_type.toLowerCase()),
          )?.id ?? "",
        );
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setCaseLoad({
          patientId,
          error: messageOf(error),
          denied: error instanceof ClinicalWorkspaceApiError && [401, 403, 404].includes(error.status),
        });
      });
    return () => controller.abort();
  }, [token, selectedPatientId]);

  if (!token) return <LoginForm />;

  function selectCase(clinicalCase: ClinicalCase | null) {
    setSelectedCase(clinicalCase);
    setForm(clinicalCase ? toForm(clinicalCase) : EMPTY_FORM);
    setSelectedImageId(
      clinicalCase?.attachments.find((asset) =>
        ["image/png", "image/jpeg"].includes(asset.media_type.toLowerCase()),
      )?.id ?? "",
    );
    setFeedback(null);
    setRequestError(null);
  }

  function selectPatient(patientId: string) {
    setSelectedPatientId(patientId);
    setSelectedCase(null);
    setForm(EMPTY_FORM);
    setSelectedImageId("");
    setCaseLoad(null);
  }

  async function createDraft() {
    if (!selectedPatientId) return;
    setIsCreating(true);
    setFeedback(null);
    setRequestError(null);
    try {
      const created = await createClinicalCase(selectedPatientId, { status: "draft" });
      setCaseLoad({ patientId: selectedPatientId, cases: [created, ...cases] });
      selectCase(created);
      setFeedback("Draft created. Saving a draft does not run inference.");
    } catch (error: unknown) {
      setRequestError(messageOf(error));
    } finally {
      setIsCreating(false);
    }
  }

  async function saveDraft(): Promise<ClinicalCase | null> {
    if (!selectedCase) return null;
    setIsSaving(true);
    setFeedback(null);
    setRequestError(null);
    try {
      const saved = await updateClinicalCase(selectedCase.id, toPayload(form));
      setSelectedCase(saved);
      setCaseLoad({ patientId: selectedPatientId, cases: cases.map((item) => item.id === saved.id ? saved : item) });
      setFeedback("Case draft saved. No model was run.");
      return saved;
    } catch (error: unknown) {
      setRequestError(messageOf(error));
      return null;
    } finally {
      setIsSaving(false);
    }
  }

  async function submitAnalysis() {
    if (!selectedCase) return;
    setRequestError(null);
    setFeedback(null);
    setIsSubmitting(true);
    try {
      const saved = await saveDraft();
      if (!saved) return;
      const payload: CaseAnalysisPayload = analysisType === "imaging"
        ? {
            analysis_type: "imaging",
            submit_now: true,
            asset_id: selectedImageId || undefined,
            generate_heatmap: false,
          }
        : {
            analysis_type: "tabular",
            submit_now: true,
            tabular_input: {
              age: Number(tabular.age),
              gender: Number(tabular.gender),
              smoking: Number(tabular.smoking),
              imaginary_min: tabular.imaginary_min.trim() ? Number(tabular.imaginary_min) : null,
              imaginary_avg: tabular.imaginary_avg.trim() ? Number(tabular.imaginary_avg) : null,
              real_min: tabular.real_min.trim() ? Number(tabular.real_min) : null,
              real_avg: tabular.real_avg.trim() ? Number(tabular.real_avg) : null,
            },
          };
      if (payload.analysis_type === "imaging" && !payload.asset_id) {
        throw new Error("Attach a PNG or JPEG image to this case before selecting imaging analysis.");
      }
      const run = await createCaseAnalysis(saved.id, payload);
      const runs = [run, ...saved.analysis_runs.filter((item) => item.id !== run.id)];
      const updated = { ...saved, analysis_runs: runs };
      setSelectedCase(updated);
      setCaseLoad({ patientId: selectedPatientId, cases: cases.map((item) => item.id === updated.id ? updated : item) });
      setFeedback(`Analysis run ${run.status.replaceAll("_", " ")}. Research output requires qualified human review.`);
    } catch (error: unknown) {
      setRequestError(messageOf(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  async function saveAnalysisDraft() {
    if (!selectedCase) return;
    setIsSubmitting(true);
    setRequestError(null);
    try {
      const saved = await saveDraft();
      if (!saved) return;
      const payload: CaseAnalysisPayload = analysisType === "imaging"
        ? {
            analysis_type: "imaging",
            submit_now: false,
            asset_id: selectedImageId || undefined,
            generate_heatmap: false,
          }
        : {
            analysis_type: "tabular",
            submit_now: false,
            tabular_input: tabularDraftInput(tabular),
          };
      const run = await createCaseAnalysis(saved.id, payload);
      const updated = {
        ...saved,
        analysis_runs: [run, ...saved.analysis_runs.filter((item) => item.id !== run.id)],
      };
      setSelectedCase(updated);
      setCaseLoad({ patientId: selectedPatientId, cases: cases.map((item) => item.id === updated.id ? updated : item) });
      setFeedback(`Analysis draft saved for ${run.model_name}. No model was run.`);
    } catch (error: unknown) {
      setRequestError(messageOf(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  function reopenAnalysisDraft(run: ClinicalAnalysisRun) {
    const savedInput = run.draft_input ?? {};
    if (run.model_name === "tabular_exasens_baseline") {
      setAnalysisType("tabular");
      setTabular({
        age: typeof savedInput.age === "number" ? String(savedInput.age) : "",
        gender: typeof savedInput.gender === "number" ? String(savedInput.gender) : "",
        smoking: typeof savedInput.smoking === "number" ? String(savedInput.smoking) : "",
        imaginary_min: typeof savedInput.imaginary_min === "number" ? String(savedInput.imaginary_min) : "",
        imaginary_avg: typeof savedInput.imaginary_avg === "number" ? String(savedInput.imaginary_avg) : "",
        real_min: typeof savedInput.real_min === "number" ? String(savedInput.real_min) : "",
        real_avg: typeof savedInput.real_avg === "number" ? String(savedInput.real_avg) : "",
      });
    } else {
      setAnalysisType("imaging");
      setSelectedImageId(typeof savedInput.asset_id === "string" ? savedInput.asset_id : "");
    }
    setFeedback("Saved analysis draft reopened. Update its inputs and save again when ready.");
    setRequestError(null);
  }

  async function uploadAttachment(file: File | undefined) {
    if (!selectedCase || !selectedPatientId || !file) return;
    setAttachmentBusy(true);
    setRequestError(null);
    try {
      await uploadCaseAttachment(selectedPatientId, selectedCase.id, file);
      const updated = (await fetchPatientCases(selectedPatientId)).find((item) => item.id === selectedCase.id);
      if (updated) {
        setSelectedCase(updated);
        setCaseLoad({ patientId: selectedPatientId, cases: cases.map((item) => item.id === updated.id ? updated : item) });
        if (!selectedImageId) {
          setSelectedImageId(updated.attachments.find((asset) =>
            ["image/png", "image/jpeg"].includes(asset.media_type.toLowerCase()),
          )?.id ?? "");
        }
      }
      setFeedback("Attachment uploaded and validated.");
    } catch (error: unknown) {
      setRequestError(messageOf(error));
    } finally {
      setAttachmentBusy(false);
    }
  }

  async function removeAttachment(assetId: string) {
    if (!selectedCase) return;
    setAttachmentBusy(true);
    setRequestError(null);
    try {
      await removeCaseAttachment(assetId);
      const updated = (await fetchPatientCases(selectedPatientId)).find((item) => item.id === selectedCase.id);
      if (updated) {
        setSelectedCase(updated);
        setCaseLoad({ patientId: selectedPatientId, cases: cases.map((item) => item.id === updated.id ? updated : item) });
        if (selectedImageId === assetId) {
          setSelectedImageId(updated.attachments.find((asset) =>
            ["image/png", "image/jpeg"].includes(asset.media_type.toLowerCase()),
          )?.id ?? "");
        }
      }
      setFeedback("Attachment removed.");
    } catch (error: unknown) {
      setRequestError(messageOf(error));
    } finally {
      setAttachmentBusy(false);
    }
  }

  async function actOnRun(run: ClinicalAnalysisRun, action: "submit" | "retry" | "review") {
    setRequestError(null);
    setIsSubmitting(true);
    try {
      const updatedRun = action === "submit"
        ? await submitCaseAnalysis(run.id)
        : action === "retry"
          ? await retryCaseAnalysis(run.id)
          : await reviewCaseAnalysis(run.id);
      if (!selectedCase) return;
      const updated = {
        ...selectedCase,
        analysis_runs: [updatedRun, ...selectedCase.analysis_runs.filter((item) => item.id !== updatedRun.id)],
      };
      setSelectedCase(updated);
      setCaseLoad({ patientId: selectedPatientId, cases: cases.map((item) => item.id === updated.id ? updated : item) });
    } catch (error: unknown) {
      setRequestError(messageOf(error));
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateMeasurement(index: number, patch: Partial<MeasurementDraft>) {
    setForm((current) => ({
      ...current,
      measurements: current.measurements.map((measurement, itemIndex) =>
        itemIndex === index ? { ...measurement, ...patch } : measurement,
      ),
    }));
  }

  function addLaboratory() {
    setForm((current) => ({
      ...current,
      measurements: [
        ...current.measurements,
        { kind: "laboratory", code: "", display_name: "", numeric_value: "", unit: "", reference_low: "", reference_high: "" },
      ],
    }));
  }

  if (loadingPatients) return <LoadingState variant="section" label="Loading assigned patients..." />;
  if (patientLoadCurrent?.error) {
    if (patientLoadCurrent.denied) {
      return <AccessDeniedState title="Authentication required" message={patientLoadCurrent.error} />;
    }
    return <ErrorState title="Patients could not be loaded" message={patientLoadCurrent.error} />;
  }
  if (patients.length === 0) {
    return <EmptyState title="No assigned patients" description="No accessible patient records are available for this account." />;
  }
  if (loadingCases) return <LoadingState variant="section" label="Loading clinical cases..." />;
  if (currentCaseLoad?.error) {
    return currentCaseLoad.denied
      ? <AccessDeniedState title="Case access unavailable" message={currentCaseLoad.error} />
      : <ErrorState title="Clinical cases could not be loaded" message={currentCaseLoad.error} />;
  }

  const availableImages = selectedCase?.attachments.filter((asset) =>
    ["image/png", "image/jpeg"].includes(asset.media_type.toLowerCase()),
  ) ?? [];
  return (
    <div className={styles.workspace}>
      <section className={styles.toolbar} aria-label="Patient and case selection">
        <label>
          Patient
          <select value={selectedPatientId} onChange={(event) => selectPatient(event.target.value)}>
            {patients.map((patient) => (
              <option key={patient.id} value={patient.id}>{patient.mrn_pseudonym}</option>
            ))}
          </select>
        </label>
        <label>
          Case
          <select
            value={selectedCase?.id ?? ""}
            onChange={(event) => selectCase(cases.find((item) => item.id === event.target.value) ?? null)}
            disabled={!cases.length}
          >
            {cases.length === 0 && <option value="">No case drafts yet</option>}
            {cases.map((item) => (
              <option key={item.id} value={item.id}>
                {new Date(item.start_time).toLocaleString()} — {item.status.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </label>
        <Button variant="primary" onClick={createDraft} disabled={isCreating}>
          {isCreating ? "Creating..." : "New case draft"}
        </Button>
      </section>

      {requestError && <div className={styles.error} role="alert">{requestError}</div>}
      {feedback && <div className={styles.feedback} role="status">{feedback}</div>}
      {!selectedCase ? (
        <EmptyState
          title="No clinical case selected"
          description="Create a draft for the selected patient to begin documenting this encounter."
          action={{ label: "Create case draft", onClick: createDraft, variant: "primary" }}
        />
      ) : (
        <>
          <header className={styles.caseHeader}>
            <div>
              <p className={styles.eyebrow}>Patient {selectedPatient?.mrn_pseudonym}</p>
              <h2>Clinical case</h2>
              <p>Case ID <code>{selectedCase.id}</code> · {selectedCase.status.replaceAll("_", " ")}</p>
            </div>
            <div className={styles.actions}>
              <Button variant="outline" onClick={saveDraft} disabled={isSaving || isReadOnly}>
                {isSaving ? "Saving..." : "Save draft"}
              </Button>
            </div>
          </header>

          <div className={styles.grid}>
            <div className={styles.mainColumn}>
              <section className={styles.card}>
                <h3>Clinical information</h3>
                <div className={styles.formGrid}>
                  <label className={styles.fullWidth}>Symptoms
                    <textarea value={form.symptoms} onChange={(event) => setForm({ ...form, symptoms: event.target.value })} disabled={isReadOnly} rows={3} />
                  </label>
                  <label>Duration
                    <input value={form.symptom_duration} onChange={(event) => setForm({ ...form, symptom_duration: event.target.value })} disabled={isReadOnly} placeholder="e.g. 3 days" />
                  </label>
                  <label className={styles.fullWidth}>Medical history
                    <textarea value={form.medical_history} onChange={(event) => setForm({ ...form, medical_history: event.target.value })} disabled={isReadOnly} rows={3} />
                  </label>
                  <label>Medications <span>One per line</span>
                    <textarea value={form.medications} onChange={(event) => setForm({ ...form, medications: event.target.value })} disabled={isReadOnly} rows={3} />
                  </label>
                  <label>Allergies <span>One per line</span>
                    <textarea value={form.allergies} onChange={(event) => setForm({ ...form, allergies: event.target.value })} disabled={isReadOnly} rows={3} />
                  </label>
                  <label className={styles.fullWidth}>Clinical notes
                    <textarea value={form.clinical_notes} onChange={(event) => setForm({ ...form, clinical_notes: event.target.value })} disabled={isReadOnly} rows={4} />
                  </label>
                </div>
              </section>

              <section className={styles.card}>
                <div className={styles.sectionHeader}>
                  <div><h3>Vitals and laboratory results</h3><p>Values remain in the units entered. Blank values are not stored as zero.</p></div>
                  <Button variant="outline" size="sm" onClick={addLaboratory} disabled={isReadOnly}>Add lab result</Button>
                </div>
                <div className={styles.measurements}>
                  {form.measurements.map((measurement, index) => (
                    <div className={styles.measurement} key={`${measurement.code}-${index}`}>
                      <strong>{measurement.kind === "laboratory" ? "Laboratory" : "Vital"}</strong>
                      <label>{measurement.kind === "laboratory" ? "Name" : "Measurement"}
                        <input value={measurement.display_name} onChange={(event) => updateMeasurement(index, { display_name: event.target.value })} disabled={isReadOnly} />
                      </label>
                      {measurement.kind === "laboratory" && <label>Code
                        <input value={measurement.code} onChange={(event) => updateMeasurement(index, { code: event.target.value })} disabled={isReadOnly} />
                      </label>}
                      <label>Value
                        <input type="number" step="any" value={measurement.numeric_value} onChange={(event) => updateMeasurement(index, { numeric_value: event.target.value })} disabled={isReadOnly} />
                      </label>
                      <label>Unit
                        {measurement.display_name === "Temperature" ? (
                          <select value={measurement.unit} onChange={(event) => updateMeasurement(index, { unit: event.target.value })} disabled={isReadOnly}>
                            <option value="°C">°C</option><option value="°F">°F</option>
                          </select>
                        ) : <input value={measurement.unit} onChange={(event) => updateMeasurement(index, { unit: event.target.value })} disabled={isReadOnly} />}
                      </label>
                      {measurement.kind === "laboratory" && <>
                        <label>Ref. low<input type="number" step="any" value={measurement.reference_low} onChange={(event) => updateMeasurement(index, { reference_low: event.target.value })} disabled={isReadOnly} /></label>
                        <label>Ref. high<input type="number" step="any" value={measurement.reference_high} onChange={(event) => updateMeasurement(index, { reference_high: event.target.value })} disabled={isReadOnly} /></label>
                      </>}
                    </div>
                  ))}
                </div>
              </section>

              <section className={styles.card}>
                <div className={styles.sectionHeader}>
                  <div><h3>Attachments</h3><p>PDF, PNG, or JPEG; server validates content and configured size limits.</p></div>
                  <label className={styles.uploadButton}>
                    {attachmentBusy ? "Working..." : "Upload attachment"}
                    <input
                      type="file"
                      accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg"
                      disabled={attachmentBusy || isReadOnly}
                      onChange={(event) => {
                        void uploadAttachment(event.target.files?.[0]);
                        event.currentTarget.value = "";
                      }}
                    />
                  </label>
                </div>
                {selectedCase.attachments.length === 0 ? <p className={styles.muted}>No attachments on this case.</p> : (
                  <ul className={styles.attachmentList}>
                    {selectedCase.attachments.map((asset) => (
                      <li key={asset.id}>
                        <span><strong>{asset.original_filename}</strong><small>{asset.media_type} · {Math.ceil(asset.file_size_bytes / 1024)} KB</small></span>
                        <div>
                          <Button variant="outline" size="sm" onClick={() => void downloadCaseAttachment(asset).catch((error: unknown) => setRequestError(messageOf(error)))}>Download</Button>
                          <Button variant="outline" size="sm" disabled={attachmentBusy || isReadOnly} onClick={() => void removeAttachment(asset.id)}>Remove</Button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </div>

            <aside className={styles.sideColumn}>
              <section className={styles.card} aria-label="Data quality">
                <h3>Validation summary</h3>
                {selectedCase.quality.blocking_errors.length === 0
                  ? <p className={styles.good}>No blocking data-quality errors.</p>
                  : <ul className={styles.blocking}>{selectedCase.quality.blocking_errors.map((item) => <li key={item}>{item}</li>)}</ul>}
                {selectedCase.quality.warnings.length > 0 && <ul className={styles.warnings}>{selectedCase.quality.warnings.map((item) => <li key={item}>{item}</li>)}</ul>}
                <p className={styles.notice}>These checks identify missing or inconsistent data only; they do not produce clinical conclusions.</p>
              </section>

              <section className={styles.card}>
                <h3>Research analysis</h3>
                <p className={styles.muted}>Module 9 and 10 inference is experimental and requires qualified human review.</p>
                <label>Analysis service
                  <select value={analysisType} onChange={(event) => setAnalysisType(event.target.value as "tabular" | "imaging")}>
                    <option value="imaging">Chest X-ray (Module 10)</option>
                    <option value="tabular">Tabular research (Module 9)</option>
                  </select>
                </label>
                {analysisType === "imaging" ? (
                  <label>PNG/JPEG attachment
                    <select id="analysis-image" value={selectedImageId} onChange={(event) => setSelectedImageId(event.target.value)}>
                      {availableImages.length === 0 && <option value="">No supported image attached</option>}
                      {availableImages.map((asset) => <option key={asset.id} value={asset.id}>{asset.original_filename}</option>)}
                    </select>
                  </label>
                ) : (
                  <div className={styles.formGrid}>
                    <label>Age<input type="number" min="1" max="120" value={tabular.age} onChange={(event) => setTabular({ ...tabular, age: event.target.value })} /></label>
                    <label>Gender code<select value={tabular.gender} onChange={(event) => setTabular({ ...tabular, gender: event.target.value })}><option value="">Choose</option><option value="0">0</option><option value="1">1</option></select></label>
                    <label>Smoking code<select value={tabular.smoking} onChange={(event) => setTabular({ ...tabular, smoking: event.target.value })}><option value="1">1</option><option value="2">2</option><option value="3">3</option></select></label>
                    <label>Imaginary min<input type="number" step="any" value={tabular.imaginary_min} onChange={(event) => setTabular({ ...tabular, imaginary_min: event.target.value })} /></label>
                    <label>Imaginary avg<input type="number" step="any" value={tabular.imaginary_avg} onChange={(event) => setTabular({ ...tabular, imaginary_avg: event.target.value })} /></label>
                    <label>Real min<input type="number" step="any" value={tabular.real_min} onChange={(event) => setTabular({ ...tabular, real_min: event.target.value })} /></label>
                    <label>Real avg<input type="number" step="any" value={tabular.real_avg} onChange={(event) => setTabular({ ...tabular, real_avg: event.target.value })} /></label>
                  </div>
                )}
                <Button
                  variant="primary"
                  onClick={submitAnalysis}
                  disabled={isSubmitting || isReadOnly || !form.symptoms.trim() || (analysisType === "imaging" && availableImages.length === 0) || (analysisType === "tabular" && (!tabular.age || tabular.gender === ""))}
                >
                  {isSubmitting ? "Submitting..." : "Submit for research analysis"}
                </Button>
                <Button
                  variant="outline"
                  onClick={saveAnalysisDraft}
                  disabled={isSubmitting || isReadOnly}
                >
                  Save analysis draft
                </Button>
              </section>

              <section className={styles.card}>
                <h3>Analysis runs</h3>
                {selectedCase.analysis_runs.length === 0 ? <p className={styles.muted}>No analysis runs. Saving drafts does not trigger inference.</p> : (
                  <div className={styles.runList}>
                    {selectedCase.analysis_runs.map((item) => {
                      const run = item as ClinicalAnalysisRun;
                      return (
                        <article className={styles.run} key={run.id}>
                          <div className={styles.runTitle}>
                            <strong>{run.model_name}</strong>
                            <span className={styles.status} data-status={run.status}>{displayRunStatus(run)}</span>
                          </div>
                          <small>Run {run.id} · model {run.model_version}</small>
                          {run.error_message && <p className={styles.errorText}>{run.error_message}</p>}
                          {run.results_summary && <pre>{JSON.stringify(run.results_summary, null, 2)}</pre>}
                          <div className={styles.runActions}>
                            {run.status === "draft" && <>
                              <Button variant="outline" size="sm" disabled={isSubmitting} onClick={() => reopenAnalysisDraft(run)}>Reopen draft</Button>
                              <Button variant="outline" size="sm" disabled={isSubmitting} onClick={() => void actOnRun(run, "submit")}>Submit</Button>
                            </>}
                            {run.status === "failed" && <Button variant="outline" size="sm" disabled={isSubmitting} onClick={() => void actOnRun(run, "retry")}>Retry</Button>}
                            {run.status === "needs_review" && <Button variant="outline" size="sm" disabled={isSubmitting} onClick={() => void actOnRun(run, "review")}>Record human review</Button>}
                          </div>
                        </article>
                      );
                    })}
                  </div>
                )}
              </section>
            </aside>
          </div>
          <footer className={styles.safetyNotice}>
            Arogya AI is a research prototype, not a clinically validated diagnostic system. All model outputs remain subject to qualified human review.
          </footer>
        </>
      )}
    </div>
  );
}
