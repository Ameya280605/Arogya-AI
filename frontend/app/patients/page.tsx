"use client";

import React, { useState, useEffect } from "react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Toast, type ToastVariant } from "@/components/ui/Toast";
import { ErrorState } from "@/components/states/ErrorState";
import {
  PatientList,
  PatientProfile,
  RegisterPatientDialog,
  EditPatientDialog,
  NewEncounterDialog,
  RecordObservationDialog,
} from "@/components/patients";
import {
  fetchPatients,
  fetchPatientQuality,
  fetchPatientEncounters,
  fetchPatientObservations,
  fetchPatientAnalysisRuns,
  fetchPatientTimeline,
  updateEncounter,
  PatientsApiError,
} from "@/services/patients";
import type {
  AnalysisRun,
  DataQualityReport,
  Encounter,
  Observation,
  Patient,
  PatientTimelineItem,
} from "@/types/patients";
import { LoginForm } from "@/components/auth/LoginForm";
import { useAuthToken } from "@/services/auth";
import styles from "../page.module.css";

interface ToastItem {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

export default function PatientsPage() {
  // Navigation & view selection
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);

  // Patient Cohort List state
  const [patients, setPatients] = useState<Patient[]>([]);
  const [totalPatients, setTotalPatients] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 15;
  const [search, setSearch] = useState("");
  const [biologicalSex, setBiologicalSex] = useState("all");
  const [syntheticFilter, setSyntheticFilter] = useState("all");
  const [isLoadingList, setIsLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  // Selected Patient Details state
  const [quality, setQuality] = useState<DataQualityReport | null>(null);
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [observations, setObservations] = useState<Observation[]>([]);
  const [analysisRuns, setAnalysisRuns] = useState<AnalysisRun[]>([]);
  const [timeline, setTimeline] = useState<PatientTimelineItem[]>([]);
  const [isLoadingDetails, setIsLoadingDetails] = useState(false);

  // Dialog states
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isNewEncounterOpen, setIsNewEncounterOpen] = useState(false);
  const [isRecordObsOpen, setIsRecordObsOpen] = useState(false);

  // Toast feedback
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const addToast = (title: string, description?: string, variant: ToastVariant = "success") => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
    setToasts((prev) => [...prev, { id, title, description, variant }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const [refetchTrigger, setRefetchTrigger] = useState(0);
  const [detailsRefetchTrigger, setDetailsRefetchTrigger] = useState(0);

  // Authentication State
  const activeToken = useAuthToken();
  const isAuthenticated = Boolean(activeToken);

  // 1. Fetch Patient List
  useEffect(() => {
    let cancelled = false;

    async function fetchList() {
      if (!activeToken) {
        setIsLoadingList(false);
        return;
      }

      setIsLoadingList(true);
      setListError(null);
      try {
        const isSynth = syntheticFilter === "synthetic" ? true : syntheticFilter === "research" ? false : null;
        const res = await fetchPatients({
          search: search.trim() ? search.trim() : null,
          biological_sex: biologicalSex !== "all" ? biologicalSex : null,
          is_synthetic: isSynth,
          page,
          page_size: pageSize,
        });
        if (!cancelled) {
          setPatients(res.items);
          setTotalPatients(res.total);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          if (err instanceof PatientsApiError) {
            if (err.isUnauthorized) {
              setListError("Your clinical session has expired. Please sign in again.");
            } else {
              setListError(err.message);
            }
          } else {
            setListError("Failed to connect to Arogya AI backend. Verify backend is running.");
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoadingList(false);
        }
      }
    }

    fetchList();

    return () => {
      cancelled = true;
    };
  }, [activeToken, search, biologicalSex, syntheticFilter, page, pageSize, refetchTrigger]);

  // 2. Fetch Selected Patient Details
  useEffect(() => {
    if (!selectedPatient) return;

    let cancelled = false;

    async function fetchDetails() {
      if (!selectedPatient) return;
      setIsLoadingDetails(true);
      try {
        const [qualityRes, encountersRes, obsRes, runsRes, timelineRes] = await Promise.all([
          fetchPatientQuality(selectedPatient.id).catch(() => null),
          fetchPatientEncounters(selectedPatient.id, { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100 })),
          fetchPatientObservations(selectedPatient.id, { page_size: 100 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 100 })),
          fetchPatientAnalysisRuns(selectedPatient.id, { page_size: 50 }).catch(() => ({ items: [], total: 0, page: 1, page_size: 50 })),
          fetchPatientTimeline(selectedPatient.id, { limit: 50 }).catch(() => ({ patient_id: selectedPatient.id, items: [], total: 0 })),
        ]);

        if (!cancelled) {
          setQuality(qualityRes);
          setEncounters(encountersRes.items);
          setObservations(obsRes.items);
          setAnalysisRuns(runsRes.items);
          setTimeline(timelineRes.items);
        }
      } catch {
        if (!cancelled) {
          addToast("Failed to load clinical details", "Some longitudinal records could not be fetched.", "warning");
        }
      } finally {
        if (!cancelled) {
          setIsLoadingDetails(false);
        }
      }
    }

    fetchDetails();

    return () => {
      cancelled = true;
    };
  }, [selectedPatient, detailsRefetchTrigger]);

  // Handle Mark Encounter Completed
  const handleCompleteEncounter = async (encounterId: string) => {
    try {
      await updateEncounter(encounterId, {
        status: "completed",
        end_time: new Date().toISOString(),
      });
      addToast("Encounter Completed", "The encounter status has been updated to completed.");
      setDetailsRefetchTrigger((prev) => prev + 1);
    } catch {
      addToast("Failed to update encounter", "Could not complete encounter.", "danger");
    }
  };

  return (
    <PageContainer
      title={selectedPatient ? `Patient: ${selectedPatient.mrn_pseudonym}` : "Patient Intelligence"}
      description={
        selectedPatient
          ? "Longitudinal patient record, encounter episodes, physiological vitals, and data quality evaluation."
          : "Longitudinal patient cohort management, search, demographic stratification, and care episodes."
      }
      breadcrumbs={
        selectedPatient
          ? [
              { label: "Overview", href: "/" },
              { label: "Patient Intelligence", href: "/patients" },
              { label: selectedPatient.mrn_pseudonym },
            ]
          : [
              { label: "Overview", href: "/" },
              { label: "Patient Intelligence" },
            ]
      }
      badge={
        <div
          className={styles.stageBadge}
          role="status"
          aria-label="Roadmap Module 6 Active"
        >
          <span className={styles.stageDot} aria-hidden="true" style={{ background: "var(--color-success, #10b981)" }} />
          <span>Module 6: Active</span>
        </div>
      }
    >
      <div className={styles.container}>
        {/* Clinical Safety & Research Disclaimer */}
        <section
          className={styles.disclaimerBox}
          role="region"
          aria-labelledby="patients-safety-heading"
        >
          <div className={styles.disclaimerIcon} aria-hidden="true">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </div>
          <div>
            <h2 id="patients-safety-heading" className={styles.disclaimerHeading}>
              Clinical Safety Notice — Research Prototype
            </h2>
            <p className={styles.disclaimerText}>
              Patient Intelligence is an exploratory decision-support and synthetic intake interface.
              All patient identifiers, encounters, and vital sign records are strictly synthetic or licensed research fixtures.
              This system does not perform autonomous diagnosis or patient care without certified human clinician review.
            </p>
          </div>
        </section>

        {/* View Switcher: Patient List vs. Selected Patient Profile vs. Authentication Prompt */}
        {!isAuthenticated ? (
          <div style={{ maxWidth: 480, margin: "var(--space-6) auto", width: "100%" }}>
            <LoginForm
              title="Clinical Authentication Required"
              description="Patient Intelligence workflows require an active Doctor Reviewer or Administrator session (Module 7 RBAC). Sign in or choose a quick role below to access patient records."
              onSuccess={() => {
                setRefetchTrigger((prev) => prev + 1);
              }}
            />
          </div>
        ) : listError ? (
          <ErrorState
            title="Unable to load patient records"
            message={listError}
            errorCode="PATIENT_SERVICE_ERROR"
            onRetry={() => setRefetchTrigger((prev) => prev + 1)}
          />
        ) : selectedPatient ? (
          <PatientProfile
            patient={selectedPatient}
            quality={quality}
            encounters={encounters}
            observations={observations}
            analysisRuns={analysisRuns}
            timeline={timeline}
            isLoading={isLoadingDetails}
            onBack={() => {
              setSelectedPatient(null);
              setRefetchTrigger((prev) => prev + 1);
            }}
            onOpenEdit={() => setIsEditOpen(true)}
            onOpenNewEncounter={() => setIsNewEncounterOpen(true)}
            onOpenRecordObservation={() => setIsRecordObsOpen(true)}
            onCompleteEncounter={handleCompleteEncounter}
          />
        ) : (
          <PatientList
            patients={patients}
            total={totalPatients}
            page={page}
            pageSize={pageSize}
            isLoading={isLoadingList}
            search={search}
            biologicalSex={biologicalSex}
            syntheticFilter={syntheticFilter}
            onSearchChange={(val) => {
              setSearch(val);
              setPage(1);
            }}
            onBiologicalSexChange={(val) => {
              setBiologicalSex(val);
              setPage(1);
            }}
            onSyntheticFilterChange={(val) => {
              setSyntheticFilter(val);
              setPage(1);
            }}
            onPageChange={setPage}
            onSelectPatient={setSelectedPatient}
            onOpenRegister={() => setIsRegisterOpen(true)}
          />
        )}

        {/* Dialog Modals */}
        <RegisterPatientDialog
          open={isRegisterOpen}
          onOpenChange={setIsRegisterOpen}
          onSuccess={(newPatient) => {
            addToast("Patient Registered", `Successfully registered cohort record '${newPatient.mrn_pseudonym}'.`);
            setRefetchTrigger((prev) => prev + 1);
            setSelectedPatient(newPatient);
          }}
        />

        <EditPatientDialog
          open={isEditOpen}
          patient={selectedPatient}
          onOpenChange={setIsEditOpen}
          onSuccess={(updated) => {
            addToast("Profile Updated", `Demographic attributes updated for '${updated.mrn_pseudonym}'.`);
            setSelectedPatient(updated);
            setDetailsRefetchTrigger((prev) => prev + 1);
          }}
        />

        <NewEncounterDialog
          open={isNewEncounterOpen}
          patient={selectedPatient}
          onOpenChange={setIsNewEncounterOpen}
          onSuccess={() => {
            addToast("Encounter Recorded", "New clinical encounter logged in patient history.");
            setDetailsRefetchTrigger((prev) => prev + 1);
          }}
        />

        <RecordObservationDialog
          open={isRecordObsOpen}
          patient={selectedPatient}
          encounters={encounters}
          onOpenChange={setIsRecordObsOpen}
          onSuccess={(newObs) => {
            addToast("Observation Logged", `Recorded measurement '${newObs.display_name}'.`);
            setDetailsRefetchTrigger((prev) => prev + 1);
          }}
        />

        {/* Toast Notification Stream */}
        {toasts.length > 0 && (
          <div
            style={{
              position: "fixed",
              bottom: "1.5rem",
              right: "1.5rem",
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              zIndex: 9999,
            }}
            aria-live="polite"
          >
            {toasts.map((t) => (
              <Toast
                key={t.id}
                title={t.title}
                description={t.description}
                variant={t.variant}
                onClose={() => removeToast(t.id)}
              />
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  );
}

