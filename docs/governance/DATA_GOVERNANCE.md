# Arogya AI — Data Governance & Privacy Framework

> **Governance Notice:** This document establishes the foundational data policies and operational constraints for the Arogya AI project.<br/>
> The controls listed below represent **governing policies and target implementation specifications**; they do not represent completed automated technical controls at this initial repository foundation phase.

---

## 1. Data Classification Taxonomy

All data handled within the Arogya AI repository and planned services is classified into seven discrete tiers:

| Tier | Category | Description | Permitted Storage |
| :--- | :--- | :--- | :--- |
| **Tier 1** | **Synthetic Data** | Artificially generated patient profiles, simulated encounters, and synthetic lab results (e.g., Synthea, Faker). | Tracked in `data/synthetic/` |
| **Tier 2** | **Licensed Research Data** | Public, de-identified clinical datasets with documented data-use agreements (e.g., PhysioNet, NIH ChestX-ray). | Local filesystem (ignored by Git) |
| **Tier 3** | **Derived Data & Metrics** | Preprocessed features, intermediate tensors, embeddings, confusion matrices, and benchmark tables. | Local caches, evaluation reports |
| **Tier 4** | **Model Artifacts** | Trained model weights (`.pt`, `.onnx`), preprocessing transformers, and SHAP explainer objects. | Local artifact cache (ignored by Git) |
| **Tier 5** | **Knowledge Documents** | Medical practice guidelines, public PubMed abstracts, clinical ontologies used for RAG. | Tracked in `knowledge/documents/` |
| **Tier 6** | **Operational Logs** | API request logs, execution trace IDs, and performance metrics (stripped of patient details). | Ephemeral console / local log files |
| **Tier 7** | **Configuration & Secrets** | API keys, database credentials, JWT secrets, and environment parameters. | Strictly `.env` (never committed) |

---

## 2. Permitted Development Data

Only two types of clinical or patient data are permitted within development, testing, and demonstration environments:

1. **Synthetic Data:** Programmatically generated records that possess no correlation with any living or deceased individual.
2. **Authorized Public Research Datasets:** Openly published, fully anonymized scientific datasets where:
   * The license explicitly permits academic/prototyping use.
   * Required training or data-use agreements (DUAs) have been completed.
   * Dataset terms permit the intended evaluation workflow.

---

## 3. Strictly Prohibited Content (Zero Tolerance)

The following items are **strictly forbidden** from being placed into the repository, staging branches, issues, or pull requests:

* **Protected Health Information (PHI/PII):** Real patient names, birth dates, national identification numbers, phone numbers, addresses, hospital MRNs, or identifiable clinical notes.
* **Unapproved Clinical Images:** Medical scans or photographs originating from clinical facilities without documented IRB/ethics approval and verified de-identification.
* **Production Credentials & Secrets:** Database passwords, cloud access keys, third-party LLM API keys, TLS private keys, and encryption certificates.
* **Proprietary Third-Party Information:** Copyrighted medical textbooks, proprietary diagnostic software source code, or NDA-protected datasets.

---

## 4. Dataset Provenance & Tracking Standards

Every dataset introduced to Arogya AI must be accompanied by a standardized provenance record maintained in `data/schemas/` or `docs/research/`, documenting:

* **Dataset Name & Version:** Canonical name and exact release tag or download hash.
* **Provenance & Origin:** Source institution, repository URL, or generation script parameters.
* **License & Permitted Uses:** Exact license terms (e.g., CC-BY 4.0, PhysioNet Credentialed Health Data License) and restrictions.
* **Access Date:** Timestamp when the dataset was fetched or generated.
* **Preprocessing Transformations:** Clear documentation of cleaning, normalization, imputation, and train/val/test splitting logic.

---

## 5. Data Minimization & Retention Principles

* **Minimization by Design:** In future API implementations, ingestion schemas will collect only the minimum clinical features required for the specific research model (e.g., vitals and target lab values, omitting irrelevant demographic fields).
* **Target Retention:** In development environments, temporary analysis runs and intermediate tensor caches must be purged periodically. Synthetic test databases may be reset between testing milestones.
* **Secure Deletion:** When a research dataset is deprecated or permissions expire, local copies must be permanently removed from developer storage.

---

## 6. Access Control & Authorization (Target Policy)

* **Least Privilege:** Future service and administrative accounts must operate with minimal necessary privileges.
* **Role-Based Access Control (RBAC):** Planned user roles in Module 7:
  * `Administrator`: User and system configuration management; no direct patient record editing.
  * `Doctor / Reviewer`: Case intake, review queue access, report editing, and sign-off.
  * `Researcher`: Model evaluation, batch inference on synthetic datasets, and metrics inspection.

---

## 7. Logging & Telemetry Safeguards

* **Data Masking:** Application logs must record operational status (HTTP method, route, execution time, request ID, error code) while filtering out sensitive request bodies.
* **No Secret Leaks:** Log sanitization filters must redact tokens, authorization headers, and environment variables.
* **Structured Logs:** All logs will follow a structured JSON schema in future backend services to ensure auditability without unstructured free-text leaks.

---

## 8. Machine Learning Model Governance

Every research model integrated into Arogya AI must be accompanied by a standardized **Model Card** (in `ml/model_cards/`) detailing:
* Model architecture, parameter count, and base weights version.
* Training data distribution, class balance, and synthetic vs real ratio.
* Intended research task and explicit out-of-scope tasks.
* Evaluation metrics (AUROC, AUPRC, F1, Brier score calibration) across demographic subgroups.
* Known failure modes, sensitivities, and clinical limitations.

---

## 9. External Third-Party AI Services & API Policy

Before integrating any third-party external model API (e.g., OpenAI, Anthropic, Google Gemini):
1. **Privacy Review:** Verify provider terms regarding data retention, model training opt-outs, and data locality.
2. **Data Sanitation:** Ensure that only synthetic data or fully de-identified passages are transmitted.
3. **Local Alternatives:** Prioritize local, open-source model execution (e.g., via Ollama or local HuggingFace weights) where feasible for sensitive workloads.

---

## 10. Incident Handling & Accidental Exposure Response

If sensitive data (real patient information or active credentials) is accidentally committed to the repository:

1. **Immediate Containment:** Revoke exposed credentials instantly at the provider level.
2. **Repository Remediation:** Use tools such as `git-filter-repo` or BFG Repo-Cleaner to purge the sensitive commit from history; do not simply make a new commit deleting the file.
3. **Assessment & Incident Record:** Document the root cause, duration of exposure, and preventive measure in an internal security incident record.
4. **Stakeholder Notification:** Notify project leads immediately to coordinate key rotation and security audits.
