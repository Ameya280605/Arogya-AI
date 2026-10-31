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
import { createPatient, PatientsApiError } from "@/services/patients";
import type { BiologicalSex, Patient } from "@/types/patients";

export interface RegisterPatientDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (patient: Patient) => void;
}

export function RegisterPatientDialog({
  open,
  onOpenChange,
  onSuccess,
}: RegisterPatientDialogProps) {
  const [mrn, setMrn] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [biologicalSex, setBiologicalSex] = useState<BiologicalSex>("unknown");
  const [isSynthetic, setIsSynthetic] = useState(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resetForm = () => {
    setMrn("");
    setBirthDate("");
    setBiologicalSex("unknown");
    setIsSynthetic(true);
    setErrorMessage(null);
  };

  const handleClose = () => {
    resetForm();
    onOpenChange(false);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    const trimmedMrn = mrn.trim();
    if (!trimmedMrn) {
      setErrorMessage("Pseudonymous MRN is required.");
      return;
    }
    if (trimmedMrn.length < 3) {
      setErrorMessage("MRN must be at least 3 characters.");
      return;
    }

    setIsSubmitting(true);
    try {
      const newPatient = await createPatient({
        mrn_pseudonym: trimmedMrn,
        birth_date: birthDate ? birthDate : null,
        biological_sex: biologicalSex,
        is_synthetic: isSynthetic,
      });
      resetForm();
      onOpenChange(false);
      onSuccess(newPatient);
    } catch (err: unknown) {
      if (err instanceof PatientsApiError) {
        if (err.isConflict) {
          setErrorMessage(`A patient with MRN '${trimmedMrn}' already exists.`);
        } else {
          setErrorMessage(err.message);
        }
      } else {
        setErrorMessage("An unexpected error occurred while registering the patient.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Register Patient Profile</DialogTitle>
          <DialogDescription>
            Register a new synthetic or de-identified research patient cohort. Real names and identifying protected health information (PHI) are strictly forbidden.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem", marginTop: "1rem" }}>
          <FormField
            label="Pseudonymous MRN"
            required
            htmlFor="patient-mrn"
            error={errorMessage && errorMessage.includes("MRN") ? errorMessage : undefined}
            helperText="De-identified subject reference (e.g. SYNTH-PAT-0002)"
          >
            <Input
              id="patient-mrn"
              type="text"
              placeholder="e.g. SYNTH-PAT-0002"
              value={mrn}
              onChange={(e) => setMrn(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </FormField>

          <FormField
            label="Date of Birth"
            htmlFor="patient-dob"
            helperText="Reference date for demographic stratification"
          >
            <Input
              id="patient-dob"
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              disabled={isSubmitting}
            />
          </FormField>

          <FormField
            label="Biological Sex"
            htmlFor="patient-sex"
            helperText="Baseline for demographic interval calibration"
          >
            <Select
              id="patient-sex"
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
            id="patient-synthetic"
            label="Synthetic Cohort Designation"
            description="Record represents an artificially synthesized research subject with zero real human data."
            checked={isSynthetic}
            onChange={(e) => setIsSynthetic(e.target.checked)}
            disabled={isSubmitting}
          />

          {errorMessage && !errorMessage.includes("MRN") && (
            <div role="alert" style={{ color: "var(--color-danger, #ef4444)", fontSize: "0.875rem", marginTop: "0.5rem" }}>
              {errorMessage}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" type="button" onClick={handleClose} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Registering..." : "Register Patient"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
