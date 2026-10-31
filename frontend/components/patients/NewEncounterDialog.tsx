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
import { createPatientEncounter, PatientsApiError } from "@/services/patients";
import type { Encounter, EncounterStatus, EncounterType, Patient } from "@/types/patients";

export interface NewEncounterDialogProps {
  open: boolean;
  patient: Patient | null;
  onOpenChange: (open: boolean) => void;
  onSuccess: (encounter: Encounter) => void;
}

export function NewEncounterDialog({
  open,
  patient,
  onOpenChange,
  onSuccess,
}: NewEncounterDialogProps) {
  const [encounterType, setEncounterType] = useState<EncounterType>("ambulatory");
  const [status, setStatus] = useState<EncounterStatus>("in_progress");
  const [startTime, setStartTime] = useState("2026-10-27T10:00");
  const [endTime, setEndTime] = useState("");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patient) return;
    setErrorMessage(null);

    if (!startTime) {
      setErrorMessage("Commencement start time is required.");
      return;
    }

    const startIso = new Date(startTime).toISOString();
    const endIso = endTime ? new Date(endTime).toISOString() : null;

    if (endIso && endIso < startIso) {
      setErrorMessage("Conclusion time cannot be earlier than start time.");
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await createPatientEncounter(patient.id, {
        encounter_type: encounterType,
        status,
        start_time: startIso,
        end_time: endIso,
      });
      onOpenChange(false);
      onSuccess(created);
    } catch (err: unknown) {
      if (err instanceof PatientsApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to create encounter.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Record Clinical Encounter</DialogTitle>
          <DialogDescription>
            Initiate a care encounter or longitudinal evaluation for patient: <strong>{patient?.mrn_pseudonym}</strong>
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
          <FormField
            label="Encounter Type"
            htmlFor="encounter-type"
            helperText="Clinical setting classification"
          >
            <Select
              id="encounter-type"
              value={encounterType}
              onChange={(e) => setEncounterType(e.target.value as EncounterType)}
              disabled={isSubmitting}
            >
              <option value="ambulatory">Ambulatory (Outpatient)</option>
              <option value="inpatient">Inpatient (Admission)</option>
              <option value="emergency">Emergency Department</option>
              <option value="synthetic">Synthetic Study Epoch</option>
            </Select>
          </FormField>

          <FormField
            label="Initial Status"
            htmlFor="encounter-status"
            helperText="Current lifecycle state"
          >
            <Select
              id="encounter-status"
              value={status}
              onChange={(e) => setStatus(e.target.value as EncounterStatus)}
              disabled={isSubmitting}
            >
              <option value="in_progress">In-Progress</option>
              <option value="planned">Planned / Scheduled</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </Select>
          </FormField>

          <FormField
            label="Start Time"
            required
            htmlFor="encounter-start"
            helperText="Commencement timestamp"
          >
            <Input
              id="encounter-start"
              type="datetime-local"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </FormField>

          <FormField
            label="Conclusion Time (Optional)"
            htmlFor="encounter-end"
            helperText="Required if status is completed"
          >
            <Input
              id="encounter-end"
              type="datetime-local"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              disabled={isSubmitting}
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
              {isSubmitting ? "Creating..." : "Create Encounter"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
