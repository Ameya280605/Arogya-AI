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
import { FormField, Input, Select, Checkbox } from "@/components/ui/Form";
import { updatePatient, PatientsApiError } from "@/services/patients";
import type { BiologicalSex, Patient } from "@/types/patients";

export interface EditPatientDialogProps {
  open: boolean;
  patient: Patient | null;
  onOpenChange: (open: boolean) => void;
  onSuccess: (updated: Patient) => void;
}

export function EditPatientDialog({
  open,
  patient,
  onOpenChange,
  onSuccess,
}: EditPatientDialogProps) {
  const [prevPatientId, setPrevPatientId] = useState<string | null>(null);
  const [birthDate, setBirthDate] = useState("");
  const [biologicalSex, setBiologicalSex] = useState<BiologicalSex>("unknown");
  const [isSynthetic, setIsSynthetic] = useState(true);

  if (patient && patient.id !== prevPatientId) {
    setPrevPatientId(patient.id);
    setBirthDate(patient.birth_date || "");
    setBiologicalSex(patient.biological_sex || "unknown");
    setIsSynthetic(patient.is_synthetic);
  }

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patient) return;
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const updated = await updatePatient(patient.id, {
        birth_date: birthDate ? birthDate : null,
        biological_sex: biologicalSex,
        is_synthetic: isSynthetic,
      });
      onOpenChange(false);
      onSuccess(updated);
    } catch (err: unknown) {
      if (err instanceof PatientsApiError) {
        setErrorMessage(err.message);
      } else {
        setErrorMessage("Failed to update patient profile.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit Patient Profile</DialogTitle>
          <DialogDescription>
            Modify demographic stratification attributes for cohort record: <strong>{patient?.mrn_pseudonym}</strong>
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
          <FormField
            label="Date of Birth"
            htmlFor="edit-patient-dob"
            helperText="Reference date for demographic stratification"
          >
            <Input
              id="edit-patient-dob"
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              disabled={isSubmitting}
            />
          </FormField>

          <FormField
            label="Biological Sex"
            htmlFor="edit-patient-sex"
            helperText="Baseline for demographic interval calibration"
          >
            <Select
              id="edit-patient-sex"
              value={biologicalSex}
              onChange={(e) => setBiologicalSex(e.target.value as BiologicalSex)}
              disabled={isSubmitting}
            >
              <option value="unknown">Unknown / Unspecified</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </Select>
          </FormField>

          <Checkbox
            id="edit-patient-synthetic"
            label="Synthetic Cohort Designation"
            description="Preserve synthetic status for local research isolation."
            checked={isSynthetic}
            onChange={(e) => setIsSynthetic(e.target.checked)}
            disabled={isSubmitting}
          />

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
              {isSubmitting ? "Saving..." : "Save Changes"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
