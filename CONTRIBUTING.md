# Contributing to Arogya AI

Thank you for contributing to **Arogya AI**. This project is an academic and research prototype exploring multimodal healthcare intelligence, decision-support architectures, and clinical governance.

---

## 1. Project Stage & Working Principles

* **Early Foundation Stage:** The project is in active architectural development following the modular roadmap.
* **Bounded Phase Scope:** All changes must map to exactly one approved roadmap sub-phase (e.g., `Module 1, Phase 1.3`). Multi-phase monolithic changes or sweeping refactors outside the designated task scope are not accepted.
* **No Premature Feature Code:** Never build ahead of prerequisite foundations. Features must be backed by data schemas, tests, and documentation before being marked complete.

---

## 2. Branching & Commit Conventions

* **Branches:**
  * `main`: Protected baseline representing tested, verified checkpoints.
  * Feature/Phase branches: Use standard semantic naming, e.g.:
    * `phase/1.2-monorepo-structure`
    * `phase/2.1-fastapi-scaffold`
    * `fix/<issue-description>`
* **Commit Messages:**
  * Follow Conventional Commits format:
    * `feat(module): description`
    * `fix(module): description`
    * `docs(module): description`
    * `test(module): description`
    * `chore(module): description`
  * Reference the relevant module/sub-phase clearly.

---

## 3. Truthful Reporting & Verification Standards

* **Evidence-Based Acceptance:** Never report tests or commands as passing without having actually run them and inspected the output.
* **Failure Disclosure:** If a dependency fails to build, a type check fails, or an API error occurs, report the exact error transcript. Do not mask errors or silently bypass failed assertions.

---

## 4. Privacy, Data Safety & Secrets Handling

* **Synthetic Data Only:** Use synthetic records (e.g., generated with Faker, SynthHealth) or open datasets whose licenses and data-use agreements permit research use.
* **Absolute Zero PHI Policy:** Real patient names, medical record numbers, addresses, contact details, or identifiable clinical notes must **never** be placed in this repository.
* **No Hardcoded Secrets:** Passwords, API tokens, encryption keys, and connection strings must remain in untracked local `.env` files. Verify that new files are covered by `.gitignore`.

---

## 5. Clinical Safety & Medical Disclaimers

* **Research Prototype:** Arogya AI is an academic prototype. It is **not** a diagnostic device and does not have regulatory clearance.
* **No Unverified Clinical Claims:** Never present model confidence scores, consensus outputs, or heuristic metrics as validated clinical probabilities without formal calibration and peer-reviewed clinical validation.
* **Explicit Uncertainty:** Any AI-assisted workflow must support abstention, flag missing data, and preserve conflicting specialist opinions for human clinician review.

---

## 6. Repository Foundation Validation

Before submitting changes or advancing across foundation phases, execute the lightweight validation script from PowerShell to confirm repository structure, required documentation, and Git isolation boundaries:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validate_foundation.ps1
```

> **Notice:** This script validates repository structure and basic file hygiene only; it does not establish security, regulatory compliance, or clinical validity.
