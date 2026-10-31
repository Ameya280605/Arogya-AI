"use client";

import React, { useState } from "react";
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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/Tabs";
import { EmptyState } from "@/components/states/EmptyState";
import type {
  AnalysisRun,
  DataQualityReport,
  Encounter,
  Observation,
  Patient,
  PatientTimelineItem,
} from "@/types/patients";
import styles from "./PatientProfile.module.css";

export interface PatientProfileProps {
  patient: Patient;
  quality: DataQualityReport | null;
  encounters: Encounter[];
  observations: Observation[];
  analysisRuns: AnalysisRun[];
  timeline: PatientTimelineItem[];
  isLoading?: boolean;
  onBack: () => void;
  onOpenEdit: () => void;
  onOpenNewEncounter: () => void;
  onOpenRecordObservation: () => void;
  onCompleteEncounter: (encounterId: string) => void;
}

export function PatientProfile({
  patient,
  quality,
  encounters,
  observations,
  analysisRuns,
  timeline,
  isLoading = false,
  onBack,
  onOpenEdit,
  onOpenNewEncounter,
  onOpenRecordObservation,
  onCompleteEncounter,
}: PatientProfileProps) {
  const [activeTab, setActiveTab] = useState("overview");

  const calculateAge = (dobString: string | null) => {
    if (!dobString) return null;
    const parts = dobString.split("-");
    const birthYear = parseInt(parts[0], 10);
    if (isNaN(birthYear)) return null;
    const currentYear = 2026;
    const approx = currentYear - birthYear;
    return approx >= 0 ? approx : null;
  };

  const age = calculateAge(patient.birth_date);
  const score = quality?.completeness_score ?? 0;
  const scoreColor = score >= 80 ? "#10b981" : score >= 50 ? "#f59e0b" : "#ef4444";

  // Derive latest vitals for overview tab
  const getLatestVital = (codeSub: string) => {
    return observations.find((o) => (o.code || "").includes(codeSub) || (o.display_name || "").toLowerCase().includes(codeSub));
  };
  const latestHr = getLatestVital("8867-4") || getLatestVital("heart");
  const latestTemp = getLatestVital("8310-5") || getLatestVital("temp");
  const latestResp = getLatestVital("9279-1") || getLatestVital("respirat");
  const latestSpo2 = getLatestVital("2708-6") || getLatestVital("spo2") || getLatestVital("oxygen");

  return (
    <div className={styles.container}>
      {/* Top Navigation */}
      <div className={styles.topBar}>
        <Button variant="outline" size="sm" onClick={onBack} id="btn-back-to-cohort">
          ← Back to Patient Cohort
        </Button>
      </div>

      {/* Profile Header Banner */}
      <section className={styles.profileBanner} aria-label="Patient Demographic Banner">
        <div className={styles.bannerMain}>
          <div className={styles.bannerIdentity}>
            <div className={styles.avatar} aria-hidden="true">
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <div>
              <h1 className={styles.mrnTitle}>{patient.mrn_pseudonym}</h1>
              <div className={styles.badgeRow}>
                <Badge
                  variant={
                    patient.biological_sex === "female"
                      ? "info"
                      : "neutral"
                  }
                >
                  {patient.biological_sex || "Unspecified Sex"}
                </Badge>

                {patient.birth_date ? (
                  <Badge variant="neutral">
                    DOB: {patient.birth_date} {age !== null ? `(${age} years)` : ""}
                  </Badge>
                ) : (
                  <Badge variant="neutral">DOB: Missing</Badge>
                )}

                {patient.is_synthetic ? (
                  <Badge variant="warning">Synthetic Subject</Badge>
                ) : (
                  <Badge variant="success">Research Cohort</Badge>
                )}

                {isLoading && (
                  <Badge variant="neutral">Syncing...</Badge>
                )}
              </div>
            </div>
          </div>

          <div className={styles.bannerActions}>
            <Button variant="outline" size="sm" onClick={onOpenEdit} id="btn-edit-patient">
              Edit Demographics
            </Button>
            <Button variant="outline" size="sm" onClick={onOpenNewEncounter} id="btn-new-encounter">
              + New Encounter
            </Button>
            <Button variant="primary" size="sm" onClick={onOpenRecordObservation} id="btn-record-observation">
              + Record Vital / Finding
            </Button>
          </div>
        </div>

        {/* Phase 6.5: Data Quality Completeness Indicator */}
        <div className={styles.qualitySection} aria-label="Data Completeness Evaluation">
          <div className={styles.qualityHeader}>
            <span style={{ fontWeight: 600 }}>Data Quality & Completeness Score:</span>
            <span style={{ fontWeight: 700, color: scoreColor }}>
              {score}% — {score >= 80 ? "Comprehensive" : score >= 50 ? "Moderate" : "Sparse / Incomplete"}
            </span>
          </div>
          <div className={styles.progressBarContainer} role="progressbar" aria-valuenow={score} aria-valuemin={0} aria-valuemax={100}>
            <div className={styles.progressBarFill} style={{ width: `${score}%`, backgroundColor: scoreColor }} />
          </div>
        </div>

        {/* Phase 6.5: Demographic & Unit Consistency Warnings */}
        {quality?.has_warnings && quality.issues.length > 0 && (
          <div className={styles.qualityIssuesCard} role="alert" aria-label="Data Quality Warnings">
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "#f59e0b", fontWeight: 600, fontSize: "0.875rem" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                <line x1="12" y1="9" x2="12" y2="13" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
              <span>Data Quality Warnings ({quality.issues.filter((i) => i.severity !== "info").length})</span>
            </div>
            <ul className={styles.qualityIssuesList}>
              {quality.issues.map((issue, idx) => (
                <li key={idx} className={styles.qualityIssueItem}>
                  <Badge
                    variant={
                      issue.severity === "critical"
                        ? "danger"
                        : issue.severity === "warning"
                        ? "warning"
                        : "info"
                    }
                  >
                    {issue.category}
                  </Badge>
                  <span>{issue.message}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {/* Phase 6.3: Profile Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList aria-label="Patient Profile Navigation Tabs">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="history">History ({encounters.length})</TabsTrigger>
          <TabsTrigger value="allergies">Allergies</TabsTrigger>
          <TabsTrigger value="observations">Observations ({observations.length})</TabsTrigger>
          <TabsTrigger value="reports">Reports ({analysisRuns.length})</TabsTrigger>
          <TabsTrigger value="timeline">Timeline ({timeline.length})</TabsTrigger>
        </TabsList>

        {/* 1. OVERVIEW TAB */}
        <TabsContent value="overview">
          <div className={styles.tabContentCard}>
            <h2 style={{ fontSize: "1.125rem", margin: "0 0 0.5rem 0" }}>Patient Demographic & Clinical Overview</h2>
            <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: "0.875rem", margin: 0 }}>
              Summary of baseline physiological signals, clinical continuity, and research dataset categorization.
            </p>

            <div className={styles.vitalsGrid}>
              <div className={styles.vitalCard}>
                <span className={styles.vitalLabel}>Heart Rate</span>
                <span className={styles.vitalValue}>
                  {latestHr?.numeric_value ?? "—"}
                  <span className={styles.vitalUnit}>{latestHr?.unit || "bpm"}</span>
                </span>
              </div>
              <div className={styles.vitalCard}>
                <span className={styles.vitalLabel}>Body Temp</span>
                <span className={styles.vitalValue}>
                  {latestTemp?.numeric_value ?? "—"}
                  <span className={styles.vitalUnit}>{latestTemp?.unit || "°C"}</span>
                </span>
              </div>
              <div className={styles.vitalCard}>
                <span className={styles.vitalLabel}>Resp Rate</span>
                <span className={styles.vitalValue}>
                  {latestResp?.numeric_value ?? "—"}
                  <span className={styles.vitalUnit}>{latestResp?.unit || "/min"}</span>
                </span>
              </div>
              <div className={styles.vitalCard}>
                <span className={styles.vitalLabel}>Oxygen Saturation</span>
                <span className={styles.vitalValue}>
                  {latestSpo2?.numeric_value ?? "—"}
                  <span className={styles.vitalUnit}>{latestSpo2?.unit || "%"}</span>
                </span>
              </div>
            </div>

            <div style={{ marginTop: "1.5rem", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1rem" }}>
              <div style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)" }}>
                <h3 style={{ fontSize: "0.875rem", margin: "0 0 0.75rem 0", color: "#38bdf8" }}>Demographic Stratification</h3>
                <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.875rem" }}>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>Pseudonym MRN:</dt>
                  <dd style={{ margin: 0, fontWeight: 600 }}>{patient.mrn_pseudonym}</dd>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>Birth Date:</dt>
                  <dd style={{ margin: 0 }}>{patient.birth_date || "Not recorded"}</dd>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>Biological Sex:</dt>
                  <dd style={{ margin: 0 }}>{patient.biological_sex || "Unspecified"}</dd>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>Dataset Type:</dt>
                  <dd style={{ margin: 0 }}>{patient.is_synthetic ? "Synthetic Generator" : "Public Benchmark"}</dd>
                </dl>
              </div>

              <div style={{ background: "rgba(255,255,255,0.02)", padding: "1rem", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.06)" }}>
                <h3 style={{ fontSize: "0.875rem", margin: "0 0 0.75rem 0", color: "#38bdf8" }}>Clinical Continuity Metrics</h3>
                <dl style={{ margin: 0, display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.875rem" }}>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>Total Encounters:</dt>
                  <dd style={{ margin: 0, fontWeight: 600 }}>{encounters.length}</dd>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>Total Observations:</dt>
                  <dd style={{ margin: 0, fontWeight: 600 }}>{observations.length}</dd>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>AI Analysis Runs:</dt>
                  <dd style={{ margin: 0, fontWeight: 600 }}>{analysisRuns.length}</dd>
                  <dt style={{ color: "var(--text-tertiary, #94a3b8)" }}>Last Encounter:</dt>
                  <dd style={{ margin: 0 }}>
                    {encounters[0] ? new Date(encounters[0].start_time).toLocaleDateString() : "None"}
                  </dd>
                </dl>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* 2. HISTORY TAB (Encounters) */}
        <TabsContent value="history">
          <div className={styles.tabContentCard}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div>
                <h2 style={{ fontSize: "1.125rem", margin: "0 0 0.25rem 0" }}>Clinical Encounters & Care Episodes</h2>
                <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: "0.875rem", margin: 0 }}>
                  Chronological record of study interactions and ambulatory visits.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={onOpenNewEncounter}>
                + New Encounter
              </Button>
            </div>

            {encounters.length === 0 ? (
              <EmptyState
                title="No clinical encounters recorded"
                description="This patient cohort record has no documented care encounters. Record an ambulatory or synthetic study encounter to begin tracking longitudinal history."
                action={{
                  label: "Record Encounter",
                  onClick: onOpenNewEncounter,
                }}
              />
            ) : (
              <Table aria-label="Patient Encounters Table">
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Type</TableHead>
                    <TableHead scope="col">Status</TableHead>
                    <TableHead scope="col">Commencement</TableHead>
                    <TableHead scope="col">Conclusion</TableHead>
                    <TableHead scope="col" align="right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {encounters.map((enc) => (
                    <TableRow key={enc.id}>
                      <TableCell>
                        <strong style={{ textTransform: "capitalize" }}>{enc.encounter_type}</strong>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            enc.status === "completed"
                              ? "success"
                              : enc.status === "in_progress"
                              ? "info"
                              : enc.status === "planned"
                              ? "neutral"
                              : "danger"
                          }
                        >
                          {enc.status}
                        </Badge>
                      </TableCell>
                      <TableCell>{new Date(enc.start_time).toLocaleString()}</TableCell>
                      <TableCell>{enc.end_time ? new Date(enc.end_time).toLocaleString() : "Active"}</TableCell>
                      <TableCell align="right">
                        {enc.status === "in_progress" && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => onCompleteEncounter(enc.id)}
                          >
                            Mark Completed
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* 3. ALLERGIES TAB */}
        <TabsContent value="allergies">
          <div className={styles.tabContentCard}>
            <h2 style={{ fontSize: "1.125rem", margin: "0 0 0.5rem 0" }}>Allergy & Hypersensitivity Surveillance</h2>
            <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
              Active adverse drug reactions and environmental hypersensitivity profiles.
            </p>
            <EmptyState
              title="No documented allergies"
              description="No adverse drug reactions or hypersensitivities are recorded for this synthetic cohort record. Surveillance parameters remain nominal."
            />
          </div>
        </TabsContent>

        {/* 4. OBSERVATIONS TAB */}
        <TabsContent value="observations">
          <div className={styles.tabContentCard}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
              <div>
                <h2 style={{ fontSize: "1.125rem", margin: "0 0 0.25rem 0" }}>Physiological Observations & Vital Signs</h2>
                <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: "0.875rem", margin: 0 }}>
                  Standardized LOINC measurements, laboratory observations, and qualitative findings.
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={onOpenRecordObservation} disabled={encounters.length === 0}>
                + Record Observation
              </Button>
            </div>

            {observations.length === 0 ? (
              <EmptyState
                title="No observations recorded"
                description="No vital signs or laboratory observations have been documented yet. Use '+ Record Vital / Finding' to document patient measurements."
                action={
                  encounters.length > 0
                    ? {
                        label: "Record First Observation",
                        onClick: onOpenRecordObservation,
                      }
                    : undefined
                }
              />
            ) : (
              <Table aria-label="Patient Observations Table">
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Concept / Measurement</TableHead>
                    <TableHead scope="col">LOINC Code</TableHead>
                    <TableHead scope="col">Measured Value</TableHead>
                    <TableHead scope="col">Timestamp</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {observations.map((obs) => (
                    <TableRow key={obs.id}>
                      <TableCell>
                        <strong>{obs.display_name}</strong>
                      </TableCell>
                      <TableCell>
                        <code style={{ fontSize: "0.8125rem", background: "rgba(255,255,255,0.06)", padding: "2px 6px", borderRadius: "4px" }}>
                          {obs.code}
                        </code>
                      </TableCell>
                      <TableCell>
                        {obs.numeric_value !== null ? (
                          <span>
                            {obs.numeric_value} <span style={{ color: "var(--text-secondary, #94a3b8)" }}>{obs.unit || ""}</span>
                          </span>
                        ) : (
                          <span>{obs.text_value || "—"}</span>
                        )}
                      </TableCell>
                      <TableCell>{new Date(obs.observed_at).toLocaleString()}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* 5. REPORTS TAB */}
        <TabsContent value="reports">
          <div className={styles.tabContentCard}>
            <h2 style={{ fontSize: "1.125rem", margin: "0 0 0.5rem 0" }}>Research AI Evaluation & Screening Reports</h2>
            <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: "0.875rem", marginBottom: "1rem" }}>
              Experimental model analysis runs and risk screener evaluations executed for this subject.
            </p>

            {analysisRuns.length === 0 ? (
              <EmptyState
                title="No analysis runs scheduled"
                description="No machine learning evaluations or risk screeners have been requested for this patient. AI evaluation runs can be scheduled in the Clinical Workspace (Module 8)."
              />
            ) : (
              <Table aria-label="Patient Analysis Runs Table">
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">Model Identifier</TableHead>
                    <TableHead scope="col">Version</TableHead>
                    <TableHead scope="col">Status</TableHead>
                    <TableHead scope="col">Evaluation Summary</TableHead>
                    <TableHead scope="col">Completed</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {analysisRuns.map((run) => (
                    <TableRow key={run.id}>
                      <TableCell>
                        <strong>{run.model_name}</strong>
                      </TableCell>
                      <TableCell>
                        <Badge variant="neutral">{run.model_version}</Badge>
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            run.status === "completed"
                              ? "success"
                              : run.status === "running"
                              ? "info"
                              : run.status === "failed"
                              ? "danger"
                              : "neutral"
                          }
                        >
                          {run.status}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {run.results_summary ? (
                          <span style={{ fontSize: "0.8125rem" }}>
                            Risk Score: {String(run.results_summary.risk_score ?? "N/A")} | {String(run.results_summary.label ?? "")}
                          </span>
                        ) : (
                          <span style={{ color: "var(--text-tertiary, #64748b)" }}>Pending completion</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </TabsContent>

        {/* 6. TIMELINE TAB */}
        <TabsContent value="timeline">
          <div className={styles.tabContentCard}>
            <h2 style={{ fontSize: "1.125rem", margin: "0 0 0.5rem 0" }}>Longitudinal Clinical Event Stream</h2>
            <p style={{ color: "var(--text-secondary, #94a3b8)", fontSize: "0.875rem", marginBottom: "1.5rem" }}>
              Unified chronological history of encounters, physiological measurements, and evaluations.
            </p>

            {timeline.length === 0 ? (
              <EmptyState
                title="No timeline events recorded"
                description="Clinical timeline will populate as encounters, vitals, and analyses are recorded."
              />
            ) : (
              <div className={styles.timelineStream}>
                {timeline.map((item) => (
                  <div key={item.id} className={styles.timelineItem}>
                    <div className={styles.timelineDot} />
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <Badge
                        variant={
                          item.event_type === "encounter"
                            ? "info"
                            : item.event_type === "observation"
                            ? "neutral"
                            : item.event_type === "analysis_run"
                            ? "success"
                            : "neutral"
                        }
                      >
                        {item.event_type.replace("_", " ")}
                      </Badge>
                      <strong style={{ fontSize: "0.9375rem" }}>{item.title}</strong>
                      <span style={{ marginLeft: "auto", fontSize: "0.75rem", color: "var(--text-tertiary, #94a3b8)" }}>
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                    </div>
                    {item.description && (
                      <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.8125rem", color: "var(--text-secondary, #cbd5e1)" }}>
                        {item.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
