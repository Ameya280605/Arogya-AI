"use client";

import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { FormField, Input, Select } from "@/components/ui/Form";
import { createEncounterObservation, PatientsApiError } from "@/services/patients";
import type { Encounter, Observation, Patient } from "@/types/patients";

export interface RecordObservationDialogProps {
  open: boolean;
  patient: Patient | null;
  encounters: Encounter[];
  onOpenChange: (open: boolean) => void;
  onSuccess: (observation: Observation) => void;
}

const OBSERVATION_PRESETS = [
  { code: "8867-4", name: "Heart Rate", unit: "bpm", type: "numeric" },
  { code: "8310-5", name: "Body Temperature", unit: "Cel", type: "numeric" },
  { code: "9279-1", name: "Respiratory Rate", unit: "/min", type: "numeric" },
  { code: "2708-6", name: "Oxygen Saturation (SpO2)", unit: "%", type: "numeric" },
  { code: "8480-6", name: "Systolic Blood Pressure", unit: "mmHg", type: "numeric" },
  { code: "8462-4", name: "Diastolic Blood Pressure", unit: "mmHg", type: "numeric" },
  { code: "49727-2", name: "Cough Symptom Assessment", unit: "", type: "text" },
  { code: "custom", name: "Custom Measurement / LOINC Code", unit: "", type: "custom" },
];

export function RecordObservationDialog({
  open,
  patient,
  encounters,
  onOpenChange,
  onSuccess,
}: RecordObservationDialogProps) {
  const [selectedEncounterId, setSelectedEncounterId] = useState("");
  const effectiveEncounterId = selectedEncounterId || (encounters.length > 0 ? encounters[0].id : "");
  const [selectedPreset, setSelectedPreset] = useState("8867-4");
  const [code, setCode] = useState("8867-4");
  const [displayName, setDisplayName] = useState("Heart Rate");
  const [numericValue, setNumericValue] = useState("");
  const [textValue, setTextValue] = useState("");
  const [unit, setUnit] = useState("bpm");
  const [observedAt, setObservedAt] = useState("2026-10-27T12:00");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handlePresetChange = (presetCode: string) => {
    setSelectedPreset(presetCode);
    const preset = OBSERVATION_PRESETS.find((p) => p.code === presetCode);
    if (preset && preset.code !== "custom") {
      setCode(preset.code);
      setDisplayName(preset.name);
      setUnit(preset.unit);
    } else {
      setCode("");
      setDisplayName("");
      setUnit("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!effectiveEncounterId) {
      setErrorMessage("An associated clinical encounter is required to record observations.");
      return;
    }
    if (!code.trim() || !displayName.trim()) {
      setErrorMessage("Observation code and display name are required.");
      return;
    }

    const hasNumeric = numericValue.trim() !== "";
    const hasText = textValue.trim() !== "";
    if (!hasNumeric && !hasText) {
      setErrorMessage("Please provide either a numeric value or a qualitative text finding.");
      return;
    }

    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const created = await createEncounterObservation(effectiveEncounterId, {
        code: code.trim(),
        display_name: displayName.trim(),
        numeric_value: hasNumeric ? parseFloat(numericValue) : null,
        text_value: hasText ? textValue.trim() : null,
        unit: unit.trim() ? unit.trim() : null,
        observed_at: new Date(observedAt).toISOString(),
      });
      onOpenChange(false);
      onSuccess(created);
    } catch (err: unknown) {
      if (err instanceof PatientsApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to record observation.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Clinical Observation / Vital Sign</DialogTitle>
          <DialogDescription>
            Record ground-truth physiological vitals or lab findings for patient: <strong>{patient?.mrn_pseudonym}</strong>
          </DialogDescription>
        </DialogHeader>

        {encounters.length === 0 ? (
          <div role="alert" style={{ padding: "1rem", background: "rgba(239, 68, 68, 0.1)", borderRadius: "var(--radius-md, 8px)", border: "1px solid rgba(239, 68, 68, 0.3)", margin: "1rem 0" }}>
            <p style={{ margin: 0, fontSize: "0.875rem", color: "var(--color-danger, #ef4444)" }}>
              <strong>No Clinical Encounter Found:</strong> Observations must strictly link to an active encounter. Please create an encounter first.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
            <FormField
              label="Associated Encounter"
              required
              htmlFor="obs-encounter"
              helperText="Encounter context for this measurement"
            >
              <Select
                id="obs-encounter"
                value={effectiveEncounterId}
                onChange={(e) => setSelectedEncounterId(e.target.value)}
                disabled={isSubmitting}
                required
              >
                {encounters.map((enc) => (
                  <option key={enc.id} value={enc.id}>
                    {enc.encounter_type.toUpperCase()} ({enc.status}) — Started {new Date(enc.start_time).toLocaleDateString()}
                  </option>
                ))}
              </Select>
            </FormField>

            <FormField
              label="Concept Preset"
              htmlFor="obs-preset"
              helperText="Standard LOINC measurement types"
            >
              <Select
                id="obs-preset"
                value={selectedPreset}
                onChange={(e) => handlePresetChange(e.target.value)}
                disabled={isSubmitting}
              >
                {OBSERVATION_PRESETS.map((p) => (
                  <option key={p.code} value={p.code}>
                    {p.name} {p.code !== "custom" ? `(LOINC: ${p.code})` : ""}
                  </option>
                ))}
              </Select>
            </FormField>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 2fr", gap: "1rem" }}>
              <FormField label="LOINC Code" required htmlFor="obs-code">
                <Input
                  id="obs-code"
                  type="text"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  disabled={isSubmitting || selectedPreset !== "custom"}
                  required
                />
              </FormField>
              <FormField label="Concept Title" required htmlFor="obs-name">
                <Input
                  id="obs-name"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  disabled={isSubmitting || selectedPreset !== "custom"}
                  required
                />
              </FormField>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "1rem" }}>
              <FormField label="Numeric Value" htmlFor="obs-num-val">
                <Input
                  id="obs-num-val"
                  type="number"
                  step="any"
                  placeholder="e.g. 72"
                  value={numericValue}
                  onChange={(e) => setNumericValue(e.target.value)}
                  disabled={isSubmitting}
                />
              </FormField>
              <FormField label="Unit" htmlFor="obs-unit" helperText="e.g. bpm, Cel, %">
                <Input
                  id="obs-unit"
                  type="text"
                  placeholder="e.g. bpm"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  disabled={isSubmitting}
                />
              </FormField>
            </div>

            <FormField label="Text Finding / Qualitative Note" htmlFor="obs-text-val">
              <Input
                id="obs-text-val"
                type="text"
                placeholder="e.g. Regular sinus rhythm"
                value={textValue}
                onChange={(e) => setTextValue(e.target.value)}
                disabled={isSubmitting}
              />
            </FormField>

            <FormField label="Acquisition Timestamp" required htmlFor="obs-timestamp">
              <Input
                id="obs-timestamp"
                type="datetime-local"
                value={observedAt}
                onChange={(e) => setObservedAt(e.target.value)}
                disabled={isSubmitting}
                required
              />
            </FormField>

            {errorMessage && (
              <div role="alert" style={{ color: "var(--color-danger, #ef4444)", fontSize: "0.875rem" }}>
                {errorMessage}
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" type="button" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button variant="primary" type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Recording..." : "Record Observation"}
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
