import React from "react";
import { describe, it } from "node:test";
import assert from "node:assert";
import { renderToStaticMarkup } from "react-dom/server";

import {
  PatientList,
  PatientProfile,
  RegisterPatientDialog,
  EditPatientDialog,
  NewEncounterDialog,
  RecordObservationDialog,
} from "../components/patients";
import PatientsPage from "../app/patients/page";
import type {
  AnalysisRun,
  DataQualityReport,
  Encounter,
  Observation,
  Patient,
  PatientTimelineItem,
} from "../types/patients";

const MOCK_PATIENT: Patient = {
  id: "pat-1111-2222-3333",
  mrn_pseudonym: "SYNTH-PAT-0001",
  birth_date: "1980-01-01",
  biological_sex: "female",
  is_synthetic: true,
  created_at: "2026-01-10T08:00:00Z",
  updated_at: "2026-01-10T08:00:00Z",
};

const MOCK_QUALITY: DataQualityReport = {
  patient_id: "pat-1111-2222-3333",
  completeness_score: 85,
  demographic_score: 90,
  clinical_score: 80,
  issues: [
    {
      category: "unit",
      severity: "warning",
      field: "obs:8310-5",
      message: "Numeric observation 'Body Temperature' lacks standard unit.",
    },
  ],
  has_warnings: true,
};

const MOCK_ENCOUNTERS: Encounter[] = [
  {
    id: "enc-1111",
    patient_id: "pat-1111-2222-3333",
    encounter_type: "ambulatory",
    status: "in_progress",
    start_time: "2026-10-25T10:00:00Z",
    end_time: null,
    created_at: "2026-10-25T10:00:00Z",
    updated_at: "2026-10-25T10:00:00Z",
  },
];

const MOCK_OBSERVATIONS: Observation[] = [
  {
    id: "obs-1111",
    encounter_id: "enc-1111",
    patient_id: "pat-1111-2222-3333",
    code: "8867-4",
    display_name: "Heart Rate",
    numeric_value: 74,
    text_value: null,
    unit: "bpm",
    observed_at: "2026-10-25T10:15:00Z",
    created_at: "2026-10-25T10:15:00Z",
  },
];

const MOCK_RUNS: AnalysisRun[] = [
  {
    id: "run-1111",
    patient_id: "pat-1111-2222-3333",
    model_name: "synthetic_baseline_screener",
    model_version: "v0.1.0-demo",
    status: "completed",
    results_summary: { risk_score: 0.12, label: "nominal" },
    completed_at: "2026-10-25T10:30:00Z",
    created_at: "2026-10-25T10:25:00Z",
  },
];

const MOCK_TIMELINE: PatientTimelineItem[] = [
  {
    id: "time-1",
    event_type: "encounter",
    title: "Ambulatory Encounter",
    description: "Status: in_progress",
    timestamp: "2026-10-25T10:00:00Z",
    status: "in_progress",
  },
  {
    id: "time-2",
    event_type: "observation",
    title: "Observation: Heart Rate",
    description: "Recorded: 74 bpm",
    timestamp: "2026-10-25T10:15:00Z",
    status: "recorded",
  },
];

describe("Module 6: PatientList Component", () => {
  it("renders search, filters, register action, and populated patient table", () => {
    const html = renderToStaticMarkup(
      <PatientList
        patients={[MOCK_PATIENT]}
        total={1}
        page={1}
        pageSize={10}
        isLoading={false}
        search=""
        biologicalSex="all"
        syntheticFilter="all"
        onSearchChange={() => {}}
        onBiologicalSexChange={() => {}}
        onSyntheticFilterChange={() => {}}
        onPageChange={() => {}}
        onSelectPatient={() => {}}
        onOpenRegister={() => {}}
      />
    );

    assert.ok(html.includes("SYNTH-PAT-0001"));
    assert.ok(html.includes("female"));
    assert.ok(html.includes("Synthetic"));
    assert.ok(html.includes("Register Patient"));
    assert.ok(html.includes("View Profile"));
  });

  it("renders honest empty state when patient list is empty", () => {
    const html = renderToStaticMarkup(
      <PatientList
        patients={[]}
        total={0}
        page={1}
        pageSize={10}
        isLoading={false}
        search="NONEXISTENT"
        biologicalSex="all"
        syntheticFilter="all"
        onSearchChange={() => {}}
        onBiologicalSexChange={() => {}}
        onSyntheticFilterChange={() => {}}
        onPageChange={() => {}}
        onSelectPatient={() => {}}
        onOpenRegister={() => {}}
      />
    );

    assert.ok(html.includes("No matching patients found"));
    assert.ok(html.includes("NONEXISTENT"));
  });

  it("renders accessible loading skeleton when isLoading is true", () => {
    const html = renderToStaticMarkup(
      <PatientList
        patients={[]}
        total={0}
        page={1}
        pageSize={10}
        isLoading={true}
        search=""
        biologicalSex="all"
        syntheticFilter="all"
        onSearchChange={() => {}}
        onBiologicalSexChange={() => {}}
        onSyntheticFilterChange={() => {}}
        onPageChange={() => {}}
        onSelectPatient={() => {}}
        onOpenRegister={() => {}}
      />
    );

    assert.ok(html.includes('aria-busy="true"'));
  });
});

describe("Module 6: PatientProfile Component", () => {
  it("renders demographic banner, data quality score, and consistency warnings", () => {
    const html = renderToStaticMarkup(
      <PatientProfile
        patient={MOCK_PATIENT}
        quality={MOCK_QUALITY}
        encounters={MOCK_ENCOUNTERS}
        observations={MOCK_OBSERVATIONS}
        analysisRuns={MOCK_RUNS}
        timeline={MOCK_TIMELINE}
        isLoading={false}
        onBack={() => {}}
        onOpenEdit={() => {}}
        onOpenNewEncounter={() => {}}
        onOpenRecordObservation={() => {}}
        onCompleteEncounter={() => {}}
      />
    );

    assert.ok(html.includes("SYNTH-PAT-0001"));
    assert.ok(html.includes("85%"));
    assert.ok(html.includes("Data Quality Warnings"));
    assert.ok(html.includes("lacks standard unit"));
    assert.ok(html.includes("Heart Rate"));
    assert.ok(html.includes("74"));
    assert.ok(html.includes("bpm"));
    assert.ok(html.includes("History (1)"));
    assert.ok(html.includes("Observations (1)"));
    assert.ok(html.includes("Reports (1)"));
    assert.ok(html.includes("Timeline (2)"));
  });
});

describe("Module 6: Dialog Modals", () => {
  it("renders RegisterPatientDialog with schema fields", () => {
    const html = renderToStaticMarkup(
      <RegisterPatientDialog
        open={true}
        onOpenChange={() => {}}
        onSuccess={() => {}}
      />
    );

    assert.ok(html.includes("Register Patient Profile"));
    assert.ok(html.includes("Pseudonymous MRN"));
    assert.ok(html.includes("Date of Birth"));
    assert.ok(html.includes("Biological Sex"));
    assert.ok(html.includes("Synthetic Cohort Designation"));
  });

  it("renders EditPatientDialog with prefilled demographics", () => {
    const html = renderToStaticMarkup(
      <EditPatientDialog
        open={true}
        patient={MOCK_PATIENT}
        onOpenChange={() => {}}
        onSuccess={() => {}}
      />
    );

    assert.ok(html.includes("Edit Patient Profile"));
    assert.ok(html.includes("SYNTH-PAT-0001"));
    assert.ok(html.includes("Save Changes"));
  });

  it("renders NewEncounterDialog with encounter types and status options", () => {
    const html = renderToStaticMarkup(
      <NewEncounterDialog
        open={true}
        patient={MOCK_PATIENT}
        onOpenChange={() => {}}
        onSuccess={() => {}}
      />
    );

    assert.ok(html.includes("Record Clinical Encounter"));
    assert.ok(html.includes("Ambulatory"));
    assert.ok(html.includes("SYNTH-PAT-0001"));
  });

  it("renders RecordObservationDialog with concept presets", () => {
    const html = renderToStaticMarkup(
      <RecordObservationDialog
        open={true}
        patient={MOCK_PATIENT}
        encounters={MOCK_ENCOUNTERS}
        onOpenChange={() => {}}
        onSuccess={() => {}}
      />
    );

    assert.ok(html.includes("Record Clinical Observation"));
    assert.ok(html.includes("LOINC Code"));
    assert.ok(html.includes("Numeric Value"));
    assert.ok(html.includes("Unit"));
  });
});

describe("Module 6: Patients Page Integration", () => {
  it("renders page container with active badge, research disclaimer, and search landmark", () => {
    const html = renderToStaticMarkup(<PatientsPage />);

    assert.ok(html.includes("Patient Intelligence"));
    assert.ok(html.includes("Module 6: Active"));
    assert.ok(html.includes("Clinical Safety Notice"));
    assert.ok(html.includes("Research Prototype"));
  });
});
