# Arogya AI — Intended Use, Explicit Non-Goals & Clinical Safety Principles

> **Notice:** This document defines the operational boundaries and clinical safety policies of the Arogya AI project. Arogya AI is strictly an academic, research, and technical prototype.

---

## 1. Intended Use

Arogya AI is designed and developed exclusively for the following authorized purposes:

1. **Software Engineering & Architectural Prototyping:** Exploring modular monorepo architectures for complex healthcare data, multimodal modeling, and multi-agent systems.
2. **Healthcare Workflow Experimentation:** Evaluating interaction patterns, clinician review interfaces, and auditability in AI-assisted environments.
3. **Multimodal Model Evaluation:** Benchmarking structured tabular classifiers, computer vision pipelines (chest radiography), and retrieval-augmented generation (RAG) against established baselines.
4. **Explainability & Uncertainty Research:** Investigating feature attribution methods (SHAP), saliency visualization (Grad-CAM), calibration techniques, and abstention policies in medical research contexts.
5. **Clinician-Supervised Demonstrations:** Demonstrating proof-of-concept workflows in academic and research settings using **synthetic patient records** or appropriately licensed, de-identified public research datasets.

---

## 2. Explicit Non-Goals

To prevent misuse, over-reliance, or safety hazards, the following boundaries represent **explicit non-goals** of the Arogya AI project. Arogya AI must **never** be used for or represented as:

* **A Replacement for Clinicians:** Arogya AI does not replace licensed medical doctors, radiologists, nurses, or other healthcare professionals.
* **Autonomous Diagnostic or Treatment Device:** Arogya AI is not an autonomous diagnostic, triaging, prescribing, or therapeutic decision-making tool.
* **Certified Medical Device:** Arogya AI has not undergone clinical trials, has not received regulatory clearance or approval (e.g., from CDSCO, US FDA, EMA, or CE marking), and does not qualify as Software as a Medical Device (SaMD).
* **Direct Patient-Facing Advice System:** Arogya AI must never interact directly with patients or provide autonomous consumer health advice without clinician mediation.
* **A Guarantee of Clinical Accuracy or Patient Safety:** Machine learning outputs, probabilistic agent summaries, and literature retrievals may contain errors, biases, or omissions. No assurance or guarantee of accuracy or outcome is provided.
* **An Authority for Consequential Clinical Decisions:** Consequential clinical actions (e.g., surgical interventions, medication changes, discharge decisions) must never be executed based on Arogya AI outputs without independent clinician evaluation.

---

## 3. Clinical Safety Principles

All development within Arogya AI must strictly conform to these safety tenets:

1. **Clear Delineation Between Prediction and Fact:**
   * AI-generated summaries, risk scores, and interpretations must be visually and semantically distinct from confirmed patient data, laboratory values, and clinician notes.
2. **Transparent Uncertainty & Calibrated Confidence:**
   * Raw model confidence scores must never be presented as true clinical probabilities without formal calibration (e.g., Platt scaling, isotonic regression).
   * Confidence scores must be accompanied by explicit indicators of data quality, missing inputs, and model limitations.
3. **Mandatory Abstention Mechanisms:**
   * If input data is incomplete, out-of-distribution, physiologically inconsistent, or lacking sufficient medical evidence, the system must **abstain** from generating speculative findings and prompt for human review.
4. **Zero Tolerance for Hallucination:**
   * Medical citations, literature references, laboratory findings, or patient history must never be fabricated. Retrieval systems must link claims to verifiable text passages.
5. **Mandatory Human-in-the-Loop Review:**
   * Any generated clinical analysis must pass through a structured review workflow where qualified professionals can inspect, edit, accept, or reject findings. Original AI outputs and clinician modifications must be archived separately.
6. **No Real Patient Identifiable Data (Zero PHI):**
   * Development, evaluation, and demonstrations must rely solely on synthetic or de-identified public research datasets. Identifiable patient data must never enter the repository or system environments.

---

## 4. Pre-Deployment Regulatory & Clinical Reassessment

Before any transition from this academic prototype toward real-world hospital deployment or clinical evaluation, project stakeholders must conduct formal reassessments with qualified medical, legal, and regulatory experts:

* **Regulatory Compliance:** Evaluation against applicable regulatory frameworks, including the Indian Central Drugs Standard Control Organisation (CDSCO) Medical Device Rules, US FDA SaMD guidance, and EU AI Act high-risk classifications.
* **Clinical Validation:** Prospective, multi-center clinical trials evaluating sensitivity, specificity, positive predictive value, clinical utility, and subgroup demographic fairness.
* **Data Privacy & Ethics:** Compliance with India's Digital Personal Data Protection Act (DPDP Act 2023), HIPAA, GDPR, and formal Institutional Ethics Committee (IEC) / Institutional Review Board (IRB) review.
* **Cybersecurity & Quality Management:** Formal adherence to ISO 13485 (Medical devices quality management) and ISO 14971 (Application of risk management to medical devices).
