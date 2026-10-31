"use client";

import React from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from "@/components/ui/Table";
import { FormField, Input, Select } from "@/components/ui/Form";
import { EmptyState } from "@/components/states/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import type { Patient } from "@/types/patients";
import styles from "./PatientList.module.css";

export interface PatientListProps {
  patients: Patient[];
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  search: string;
  biologicalSex: string;
  syntheticFilter: string;
  onSearchChange: (val: string) => void;
  onBiologicalSexChange: (val: string) => void;
  onSyntheticFilterChange: (val: string) => void;
  onPageChange: (newPage: number) => void;
  onSelectPatient: (patient: Patient) => void;
  onOpenRegister: () => void;
}

export function PatientList({
  patients,
  total,
  page,
  pageSize,
  isLoading,
  search,
  biologicalSex,
  syntheticFilter,
  onSearchChange,
  onBiologicalSexChange,
  onSyntheticFilterChange,
  onPageChange,
  onSelectPatient,
  onOpenRegister,
}: PatientListProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const calculateAge = (dobString: string | null) => {
    if (!dobString) return null;
    const parts = dobString.split("-");
    const birthYear = parseInt(parts[0], 10);
    if (isNaN(birthYear)) return null;
    const currentYear = 2026;
    const approx = currentYear - birthYear;
    return approx >= 0 ? approx : null;
  };

  return (
    <div className={styles.container}>
      {/* Search and Filters Bar */}
      <section className={styles.filterCard} aria-label="Patient Cohort Search and Filters">
        <div className={styles.searchGroup}>
          <FormField label="Search Cohort" htmlFor="patient-search-input">
            <Input
              id="patient-search-input"
              type="search"
              placeholder="Filter by pseudonymous MRN..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              disabled={isLoading}
            />
          </FormField>
        </div>

        <div className={styles.filtersGroup}>
          <FormField label="Biological Sex" htmlFor="filter-sex-select">
            <Select
              id="filter-sex-select"
              value={biologicalSex}
              onChange={(e) => onBiologicalSexChange(e.target.value)}
              disabled={isLoading}
            >
              <option value="all">All Sexes</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
              <option value="unknown">Unknown</option>
            </Select>
          </FormField>

          <FormField label="Cohort Designation" htmlFor="filter-synth-select">
            <Select
              id="filter-synth-select"
              value={syntheticFilter}
              onChange={(e) => onSyntheticFilterChange(e.target.value)}
              disabled={isLoading}
            >
              <option value="all">All Cohorts</option>
              <option value="synthetic">Synthetic Only</option>
              <option value="research">Licensed Research Only</option>
            </Select>
          </FormField>
        </div>

        <div className={styles.actionsGroup}>
          <Button variant="primary" onClick={onOpenRegister} id="btn-register-patient">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              style={{ marginRight: "0.5rem" }}
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            Register Patient
          </Button>
        </div>
      </section>

      {/* Patient Table Container */}
      <div className={styles.tableContainer}>
        {isLoading ? (
          <div style={{ padding: "1.5rem" }} role="status" aria-busy="true" aria-label="Loading patient records">
            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
              <Skeleton height="2.5rem" />
              <Skeleton height="3rem" />
              <Skeleton height="3rem" />
              <Skeleton height="3rem" />
            </div>
          </div>
        ) : patients.length === 0 ? (
          <div style={{ padding: "3rem 1.5rem" }}>
            <EmptyState
              title={search ? "No matching patients found" : "No patient records registered"}
              description={
                search
                  ? `No patient records match the search filter '${search}'. Clear your search filter or register a new patient.`
                  : "The patient cohort database is currently empty. Register a synthetic subject to begin clinical evaluation."
              }
              action={{
                label: "Register New Patient",
                onClick: onOpenRegister,
              }}
            />
          </div>
        ) : (
          <>
            <Table aria-label="Patient Cohort Table">
              <TableHeader>
                <TableRow>
                  <TableHead scope="col">Subject MRN</TableHead>
                  <TableHead scope="col">Biological Sex</TableHead>
                  <TableHead scope="col">Birth Date & Age</TableHead>
                  <TableHead scope="col">Designation</TableHead>
                  <TableHead scope="col">Registered</TableHead>
                  <TableHead scope="col" align="right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {patients.map((pat) => {
                  const age = calculateAge(pat.birth_date);
                  return (
                    <TableRow key={pat.id}>
                      <TableCell>
                        <div className={styles.mrnCell}>
                          <div className={styles.mrnIcon} aria-hidden="true">
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                              <circle cx="12" cy="7" r="4" />
                            </svg>
                          </div>
                          <span>{pat.mrn_pseudonym}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            pat.biological_sex === "female"
                              ? "info"
                              : "neutral"
                          }
                        >
                          {pat.biological_sex || "unknown"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {pat.birth_date ? (
                          <span>
                            {pat.birth_date} {age !== null ? `(${age}y)` : ""}
                          </span>
                        ) : (
                          <span style={{ color: "var(--text-tertiary, #64748b)" }}>Unrecorded</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {pat.is_synthetic ? (
                          <Badge variant="warning">Synthetic</Badge>
                        ) : (
                          <Badge variant="success">Research</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {new Date(pat.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => onSelectPatient(pat)}
                          aria-label={`View profile for patient ${pat.mrn_pseudonym}`}
                        >
                          View Profile →
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>

            {/* Pagination Controls */}
            <div className={styles.paginationBar}>
              <span>
                Showing {Math.min((page - 1) * pageSize + 1, total)} to{" "}
                {Math.min(page * pageSize, total)} of {total} patient profiles
              </span>

              <div className={styles.paginationControls}>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1 || isLoading}
                  onClick={() => onPageChange(page - 1)}
                  aria-label="Previous page"
                >
                  ← Prev
                </Button>
                <span style={{ padding: "0 0.5rem" }}>
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages || isLoading}
                  onClick={() => onPageChange(page + 1)}
                  aria-label="Next page"
                >
                  Next →
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
