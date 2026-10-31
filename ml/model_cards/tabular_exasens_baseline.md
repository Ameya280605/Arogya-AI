# Model Card: Tabular Exasens Baseline (`tabular_exasens_baseline`)

**Module 9: Tabular ML Baseline Classification & Saliva Biosensor Risk Modeling**  
**Version:** `0.1.0-alpha`  
**Date:** October 2026  
**Artifact File:** `ml/tabular/artifacts/tabular_baseline.joblib`  
**Metadata:** `ml/tabular/artifacts/model_metadata.json`  

---

> [!IMPORTANT]
> **NON-DIAGNOSTIC RESEARCH PROTOTYPE DISCLAIMER**  
> This model is an experimental research prototype developed solely for exploratory decision-support demonstration and comparative benchmarking within the Arogya AI research platform. It is **NOT** a clinically validated medical device, has not received regulatory clearance (FDA, CE-IVD, CDSCO), and must **NEVER** be used as an autonomous diagnostic tool or for directing real-world clinical interventions.

---

## 1. Model Details

- **Model Name:** `tabular_exasens_baseline`
- **Model Family:** Random Forest Classifier (`sklearn.ensemble.RandomForestClassifier`)
- **Pipeline Architecture:**
  1. `SimpleImputer(strategy='median')`: Preserves full input vector integrity and allows robust fallback for unmeasured sensor signals.
  2. `RandomForestClassifier`: 100 estimators, max depth 6, min samples split 4, balanced class weighting, random state 42.
- **Target Variable:** `Diagnosis` — 4-class categorization:
  - `HC`: Healthy Control
  - `Asthma`: Asthma
  - `Infected`: Respiratory Infection
  - `COPD`: Chronic Obstructive Pulmonary Disease
- **Input Features (7 total):**
  - Demographic: `Age` (int), `Gender` (0=Female, 1=Male), `Smoking` (1=Non-smoker, 2=Ex-smoker, 3=Active-smoker)
  - Saliva Dielectric Permittivity: `Imaginary_Min`, `Imaginary_Avg`, `Real_Min`, `Real_Avg`
- **Model Checksum (SHA-256):** `a9363cee9fd4c5dd6bebbc824356b5cc1715d00906de316c67c367a9e9ddcf38`

---

## 2. Intended Use & Non-Goals

### Intended Use
- **Baseline Benchmarking:** Serves as the quantitative tabular risk reference for Module 9, to be compared against downstream multimodal agents and LLM critics (Modules 11 & 18).
- **Multi-Modal Decision Support Demonstration:** Demonstrates how laboratory biosensor data and demographic observations are consumed by Arogya AI's clinical service layer without violating data segregation boundaries.
- **Exploratory Sensitivity Analysis:** Enables research on feature attributions (SHAP) and dielectric biomarker importance in non-invasive respiratory triage.

### Out-of-Scope Non-Goals
- Autonomous diagnosis or emergency department triage.
- Standalone prescription or therapeutic recommendations.
- Replacement of spirometry, chest radiography, or microbiological culture.

---

## 3. Training & Validation Data

- **Primary Source:** Exasens respiratory biomarker dataset (`ml/tabular/data/exasens.csv`).
- **Full Cohort Context:** 399 total patient records (160 HC, 80 Asthma, 80 Infected, 79 COPD). 299 patients had demographic profiles only.
- **Complete Biosensor Training Cohort:** 100 patient cases with complete dielectric permittivity measurements:
  - `COPD`: 40 patients (40%)
  - `HC`: 40 patients (40%)
  - `Asthma`: 10 patients (10%)
  - `Infected`: 10 patients (10%)
- **Data Preprocessing & Safeguards:**
  - Patient `ID` column was strictly excluded from all training and feature matrices to eliminate label leakage.
  - Stratified 5-fold cross-validation ensured proportional representation across every training and validation split.
  - Imputation and scaling were nested inside cross-validation folds to avoid data snooping.

---

## 4. Quantitative Evaluation & Metrics

The baseline model was evaluated using 5-Fold Stratified Cross-Validation on the complete biosensor cohort ($N=100$):

| Metric | 5-Fold CV Score (Mean ± Std) | Out-of-Fold (OOF) Aggregate |
| :--- | :--- | :--- |
| **Macro F1-Score** | **0.7070 ± 0.0647** | **0.6867** |
| **Balanced Accuracy** | **0.7000 ± 0.0424** | **0.7000** |
| **Overall Accuracy** | **0.7600 ± 0.0800** | **0.7600** |

### Per-Class Out-of-Fold Performance Breakdown

| Class | Precision | Recall (Sensitivity) | F1-Score | Specificity | Support |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **COPD** | 0.878 | 0.900 | 0.889 | 0.917 | 40 |
| **HC (Healthy Control)** | 0.778 | 0.700 | 0.737 | 0.867 | 40 |
| **Infected** | 0.636 | 0.700 | 0.667 | 0.956 | 10 |
| **Asthma** | 0.417 | 0.500 | 0.455 | 0.922 | 10 |

### Out-of-Fold Confusion Matrix ($N = 100$)

```
True \ Pred        HC    Asthma  Infected      COPD
---------------------------------------------------
HC                 28         3         1         8
Asthma              1         5         3         1
Infected            1         2         7         0
COPD                2         2         0        36
```

---

## 5. Known Limitations & Failure Modes

1. **Severe Imbalance in Minority Classes:**
   The training cohort contains only 10 cases of Asthma and 10 cases of Respiratory Infection. In 5-fold validation, each fold tests against only 2 minority samples. Misclassifying a single patient drops class recall by 50%.
2. **Asthma / Infection Confusion:**
   Because inflammatory saliva markers in early-stage asthma and active infection share overlapping dielectric characteristics, the model exhibits cross-prediction between these two classes (3 false positives of Infected as Asthma, 2 false positives of Asthma as Infected).
3. **No External Clinical Validation:**
   The dataset was collected under a single experimental protocol. Generalization to other saliva collection devices, hydration states, or patient demographics cannot be guaranteed without multi-center external validation.
4. **Demographic Degradation:**
   If physical saliva dielectric readings (`Imaginary` and `Real` permittivity) are completely absent, the model relies on median imputation and demographic features (`Age`, `Gender`, `Smoking`), which degrades Macro-F1 to ~0.37–0.43.

---

## 6. Technical Reproducibility & Integrity

- **Deterministic Random Seed:** `random_state = 42` is fixed for all K-fold partitioners and tree ensembles.
- **Python Runtime:** Python 3.13.9 (`.venv`), `scikit-learn 1.9.1`, `pandas 3.1.0`, `joblib 1.6.0`.
- **Integrity Verification:** SHA-256 checksum is checked automatically on artifact loading:
  `a9363cee9fd4c5dd6bebbc824356b5cc1715d00906de316c67c367a9e9ddcf38`
- **Zero Schema Overwrite:** The artifact is stored in `ml/tabular/artifacts/` and operates strictly within the non-interfering boundaries of Module 9.

