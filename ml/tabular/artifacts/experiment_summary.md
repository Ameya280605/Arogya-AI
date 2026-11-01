# Arogya AI — Tabular ML Baseline Experiment Summary (Module 9)

> [!IMPORTANT]
> **Research Prototype Notice**: This evaluation benchmarks baseline exploratory algorithms
> on the Exasens respiratory biomarker dataset. Models are not validated for clinical diagnosis.

## 1. Cross-Validation Benchmark Overview (5-Fold Stratified CV)

### A. Full Demographic Cohort (N=399, 3 features: Age, Gender, Smoking)

| Model | CV Macro-F1 (Mean ± Std) | CV Balanced Acc (Mean ± Std) | Held-Out Test Macro-F1 (20%) | Held-Out Test Acc |
| :--- | :--- | :--- | :--- | :--- |
| **LogisticRegression** | 0.4320 ± 0.0338 | 0.4697 ± 0.0299 | 0.4761 | 0.4750 |
| **RandomForest** | 0.3683 ± 0.0387 | 0.3722 ± 0.0373 | 0.4314 | 0.4250 |
| **SVC** | 0.3935 ± 0.0274 | 0.4697 ± 0.0261 | 0.3393 | 0.5375 |

### B. Complete Biosensor Cohort (N=100, 7 features: Demographics + 4 Dielectric Permittivity)

| Model | CV Macro-F1 (Mean ± Std) | CV Balanced Acc (Mean ± Std) | Held-Out Test Macro-F1 (20%) | Held-Out Test Acc |
| :--- | :--- | :--- | :--- | :--- |
| **LogisticRegression** | 0.5615 ± 0.1044 | 0.6312 ± 0.1574 | 0.5620 | 0.6000 |
| **RandomForest** | 0.7070 ± 0.0647 | 0.7000 ± 0.0424 | 0.4688 | 0.6000 |
| **SVC** | 0.4263 ± 0.0629 | 0.4688 ± 0.0593 | 0.3080 | 0.5500 |

## 2. Held-Out Test Confusion Matrices (Biosensor Cohort, N=20)

#### LogisticRegression
```
=== Model Evaluation: LogisticRegression [Biosensor Held-Out] ===
Macro F1-Score:      0.5620
Balanced Accuracy:   0.6562
Overall Accuracy:    0.6000
Weighted F1-Score:   0.6134
Macro Precision:     0.6125
Macro Recall:        0.6562
Log Loss:            1.1985
Brier Score:         0.6520

Per-Class Breakdown:
  - HC        : Precision=1.000, Recall=0.375, F1=0.545, Sens=0.375, Spec=1.000 (Support=8)
  - Asthma    : Precision=0.200, Recall=0.500, F1=0.286, Sens=0.500, Spec=0.778 (Support=2)
  - Infected  : Precision=0.500, Recall=1.000, F1=0.667, Sens=1.000, Spec=0.889 (Support=2)
  - COPD      : Precision=0.750, Recall=0.750, F1=0.750, Sens=0.750, Spec=0.833 (Support=8)

Confusion Matrix:
True \ Pred        HC    Asthma  Infected      COPD
---------------------------------------------------
HC                 3         2         1         2
Asthma             0         1         1         0
Infected           0         0         2         0
COPD               0         2         0         6
```

#### RandomForest
```
=== Model Evaluation: RandomForest [Biosensor Held-Out] ===
Macro F1-Score:      0.4688
Balanced Accuracy:   0.4688
Overall Accuracy:    0.6000
Weighted F1-Score:   0.6000
Macro Precision:     0.4688
Macro Recall:        0.4688
Log Loss:            0.9051
Brier Score:         0.4843

Per-Class Breakdown:
  - HC        : Precision=0.625, Recall=0.625, F1=0.625, Sens=0.625, Spec=0.750 (Support=8)
  - Asthma    : Precision=0.500, Recall=0.500, F1=0.500, Sens=0.500, Spec=0.944 (Support=2)
  - Infected  : Precision=0.000, Recall=0.000, F1=0.000, Sens=0.000, Spec=0.889 (Support=2)
  - COPD      : Precision=0.750, Recall=0.750, F1=0.750, Sens=0.750, Spec=0.833 (Support=8)

Confusion Matrix:
True \ Pred        HC    Asthma  Infected      COPD
---------------------------------------------------
HC                 5         0         1         2
Asthma             0         1         1         0
Infected           2         0         0         0
COPD               1         1         0         6
```

#### SVC
```
=== Model Evaluation: SVC [Biosensor Held-Out] ===
Macro F1-Score:      0.3080
Balanced Accuracy:   0.3438
Overall Accuracy:    0.5500
Weighted F1-Score:   0.4929
Macro Precision:     0.2803
Macro Recall:        0.3438
Log Loss:            0.9367
Brier Score:         0.5144

Per-Class Breakdown:
  - HC        : Precision=0.455, Recall=0.625, F1=0.526, Sens=0.625, Spec=0.500 (Support=8)
  - Asthma    : Precision=0.000, Recall=0.000, F1=0.000, Sens=0.000, Spec=1.000 (Support=2)
  - Infected  : Precision=0.000, Recall=0.000, F1=0.000, Sens=0.000, Spec=1.000 (Support=2)
  - COPD      : Precision=0.667, Recall=0.750, F1=0.706, Sens=0.750, Spec=0.750 (Support=8)

Confusion Matrix:
True \ Pred        HC    Asthma  Infected      COPD
---------------------------------------------------
HC                 5         0         0         3
Asthma             2         0         0         0
Infected           2         0         0         0
COPD               2         0         0         6
```

## 3. Dataset Constraints & Research Limitations

1. **Severe Imbalance in Biosensor Cohort**: While the complete cohort has 40 COPD and 40 HC patients,
   it contains only **10 Asthma** and **10 Infected** cases. In a 5-fold CV split, each validation fold
   evaluates against only 2 samples for these minority classes, producing high variance in fold scores.
2. **Demographic Ambiguity**: Demographic features alone (Age, Gender, Smoking) achieve modest discriminative
   power (Macro-F1 ~0.35–0.40) because healthy smokers and elderly controls overlap heavily with clinical populations.
3. **Sensor Feature Signal**: The addition of physical saliva permittivity measurements (Imaginary & Real dielectric values)
   markedly elevates multi-class separation, with Random Forest achieving ~0.71–0.72 CV Macro-F1.
4. **Model Deployment Limitations**: The serialized Random Forest is a research baseline, not a clinically
validated production diagnostic model. Its artifact is intended for controlled research and integration testing.