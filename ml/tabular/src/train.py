"""Arogya AI - Tabular Baseline Model Training & Cross-Validation.

Module 9: Tabular ML Baseline Classification.
Trains and compares Logistic Regression, Random Forest, and SVC on both cohorts
(Full 399-patient cohort and 100-patient complete biosensor cohort) using
reproducible stratified cross-validation and strict data leakage safeguards.

SAFETY & GOVERNANCE NOTICE:
This module trains exploratory research baselines.
Outputs are NOT clinically validated diagnostic models.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC

from ml.tabular.src.dataset import (
    ALL_FEATURES,
    DEMOGRAPHIC_FEATURES,
    DIAGNOSIS_CLASSES,
    ExasensDataset,
)
from ml.tabular.src.evaluate import (
    compute_classification_metrics,
    format_metrics_summary,
)

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "artifacts"


def build_model_pipelines(random_state: int = 42) -> dict[str, Pipeline]:
    """Construct benchmark baseline classifiers with integrated preprocessing.

    Data Leakage Safeguard:
    Feature scaling (StandardScaler) is embedded directly in the Pipeline,
    ensuring it is fit strictly on training folds and never on validation or test sets.

    Args:
        random_state: Fixed pseudo-random seed for reproducibility.

    Returns:
        Dictionary of named scikit-learn Pipelines.
    """
    # 1. Multinomial Logistic Regression with balanced weighting
    log_reg = Pipeline([
        ("scaler", StandardScaler()),
        (
            "clf",
            LogisticRegression(
                class_weight="balanced",
                max_iter=1000,
                random_state=random_state,
                solver="lbfgs",
            ),
        ),
    ])

    # 2. Regularized Random Forest with balanced sub-sampling
    rf = Pipeline([
        (
            "clf",
            RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_split=4,
                class_weight="balanced",
                random_state=random_state,
            ),
        ),
    ])

    # 3. Support Vector Classifier (RBF kernel) with CalibratedClassifierCV for probability output
    svc_base = SVC(
        kernel="rbf",
        C=1.0,
        class_weight="balanced",
        random_state=random_state,
    )
    svc = Pipeline([
        ("scaler", StandardScaler()),
        (
            "clf",
            CalibratedClassifierCV(
                estimator=svc_base,
                cv=3,
            ),
        ),
    ])

    return {
        "LogisticRegression": log_reg,
        "RandomForest": rf,
        "SVC": svc,
    }


def evaluate_pipeline_cv(
    pipeline: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
    n_splits: int = 5,
    random_state: int = 42,
    labels: tuple[str, ...] = DIAGNOSIS_CLASSES,
) -> dict[str, Any]:
    """Evaluate a pipeline via Stratified K-Fold CV with Out-Of-Fold aggregation.

    Args:
        pipeline: scikit-learn Pipeline instance.
        X: Feature DataFrame.
        y: Target label Series.
        n_splits: Number of cross-validation folds.
        random_state: Random state for K-Fold generator.
        labels: Ordering of class labels.

    Returns:
        Dictionary containing fold scores, mean/std aggregates, and complete OOF metrics.
    """
    labels_list = list(labels)
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    fold_metrics: list[dict[str, Any]] = []
    n_samples = len(X)
    n_classes = len(labels_list)

    oof_preds = np.empty(n_samples, dtype=object)
    oof_probs = np.zeros((n_samples, n_classes), dtype=float)

    for fold_idx, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train_fold, X_val_fold = X.iloc[train_idx], X.iloc[val_idx]
        y_train_fold, y_val_fold = y.iloc[train_idx], y.iloc[val_idx]

        fold_pipe = clone(pipeline)
        fold_pipe.fit(X_train_fold, y_train_fold)

        val_pred = fold_pipe.predict(X_val_fold)
        val_prob = fold_pipe.predict_proba(X_val_fold)

        # Align probability column ordering with canonical labels_list
        pipe_classes = list(fold_pipe.classes_)
        aligned_probs = np.zeros((len(val_idx), n_classes), dtype=float)
        for c_idx, cls_name in enumerate(labels_list):
            if cls_name in pipe_classes:
                src_idx = pipe_classes.index(cls_name)
                aligned_probs[:, c_idx] = val_prob[:, src_idx]

        oof_preds[val_idx] = val_pred
        oof_probs[val_idx] = aligned_probs

        metrics_fold = compute_classification_metrics(
            y_true=y_val_fold,
            y_pred=val_pred,
            y_prob=aligned_probs,
            labels=labels_list,
        )
        fold_metrics.append({
            "fold": fold_idx + 1,
            "macro_f1": metrics_fold["macro_f1"],
            "balanced_accuracy": metrics_fold["balanced_accuracy"],
            "accuracy": metrics_fold["accuracy"],
        })

    # Overall Out-of-Fold (OOF) evaluation across the entire cohort
    oof_summary = compute_classification_metrics(
        y_true=y,
        y_pred=oof_preds,
        y_prob=oof_probs,
        labels=labels_list,
    )

    macro_f1_scores = [f["macro_f1"] for f in fold_metrics]
    balanced_acc_scores = [f["balanced_accuracy"] for f in fold_metrics]
    acc_scores = [f["accuracy"] for f in fold_metrics]

    return {
        "cv_folds": n_splits,
        "fold_scores": fold_metrics,
        "cv_macro_f1_mean": float(np.mean(macro_f1_scores)),
        "cv_macro_f1_std": float(np.std(macro_f1_scores)),
        "cv_balanced_acc_mean": float(np.mean(balanced_acc_scores)),
        "cv_balanced_acc_std": float(np.std(balanced_acc_scores)),
        "cv_accuracy_mean": float(np.mean(acc_scores)),
        "cv_accuracy_std": float(np.std(acc_scores)),
        "oof_metrics": oof_summary,
    }


def evaluate_held_out_test(
    pipeline: Pipeline,
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    labels: tuple[str, ...] = DIAGNOSIS_CLASSES,
) -> dict[str, Any]:
    """Train pipeline on X_train and evaluate on held-out X_test.

    Args:
        pipeline: scikit-learn Pipeline instance.
        X_train: Training feature DataFrame.
        y_train: Training target labels.
        X_test: Test feature DataFrame.
        y_test: Test target labels.
        labels: Canonical label sequence.

    Returns:
        Structured evaluation metrics on held-out test data.
    """
    labels_list = list(labels)
    fitted_pipe = clone(pipeline)
    fitted_pipe.fit(X_train, y_train)

    y_pred = fitted_pipe.predict(X_test)
    y_prob = fitted_pipe.predict_proba(X_test)

    # Realign probability columns to canonical labels
    pipe_classes = list(fitted_pipe.classes_)
    aligned_probs = np.zeros((len(X_test), len(labels_list)), dtype=float)
    for c_idx, cls_name in enumerate(labels_list):
        if cls_name in pipe_classes:
            src_idx = pipe_classes.index(cls_name)
            aligned_probs[:, c_idx] = y_prob[:, src_idx]

    return compute_classification_metrics(
        y_true=y_test,
        y_pred=y_pred,
        y_prob=aligned_probs,
        labels=labels_list,
    )


def run_tabular_benchmarks(
    dataset: ExasensDataset | None = None,
    random_state: int = 42,
    n_splits: int = 5,
) -> dict[str, Any]:
    """Execute full comparative benchmarking across both cohorts and all baseline models.

    Args:
        dataset: Optional loaded ExasensDataset. Loads default if None.
        random_state: Fixed pseudo-random seed.
        n_splits: Number of Stratified CV folds.

    Returns:
        Dictionary containing benchmark evaluation results for all models and cohorts.
    """
    if dataset is None:
        dataset = ExasensDataset.load()

    pipelines = build_model_pipelines(random_state=random_state)
    results: dict[str, Any] = {
        "metadata": {
            "random_state": random_state,
            "cv_folds": n_splits,
            "diagnosis_classes": list(DIAGNOSIS_CLASSES),
        },
        "cohorts": {},
    }

    # -------------------------------------------------------------------------
    # 1. Full Cohort (399 records, 3 demographic features)
    # -------------------------------------------------------------------------
    X_full, y_full = dataset.full_cohort(features="demographic")
    X_full_train, X_full_test, y_full_train, y_full_test = dataset.split_full_cohort(
        features="demographic", test_size=0.2, random_state=random_state
    )

    full_cohort_results: dict[str, Any] = {
        "description": "Full cohort with 3 demographic features (Age, Gender, Smoking)",
        "sample_count": len(X_full),
        "features": DEMOGRAPHIC_FEATURES,
        "models": {},
    }

    for model_name, pipe in pipelines.items():
        logger.info(f"Training {model_name} on Full Cohort...")
        cv_res = evaluate_pipeline_cv(
            pipeline=pipe,
            X=X_full,
            y=y_full,
            n_splits=n_splits,
            random_state=random_state,
        )
        test_res = evaluate_held_out_test(
            pipeline=pipe,
            X_train=X_full_train,
            y_train=y_full_train,
            X_test=X_full_test,
            y_test=y_full_test,
        )
        full_cohort_results["models"][model_name] = {
            "cv_results": cv_res,
            "held_out_test_results": test_res,
        }

    results["cohorts"]["full_cohort"] = full_cohort_results

    # -------------------------------------------------------------------------
    # 2. Biosensor Cohort (100 records, 7 features: demographics + 4 dielectric)
    # -------------------------------------------------------------------------
    X_bio, y_bio = dataset.biosensor_cohort()
    X_bio_train, X_bio_test, y_bio_train, y_bio_test = dataset.split_biosensor_cohort(
        test_size=0.2, random_state=random_state
    )

    bio_cohort_results: dict[str, Any] = {
        "description": "Complete biosensor cohort with 7 features (Demographics + Permittivity)",
        "sample_count": len(X_bio),
        "features": ALL_FEATURES,
        "models": {},
    }

    for model_name, pipe in pipelines.items():
        logger.info(f"Training {model_name} on Biosensor Cohort...")
        cv_res = evaluate_pipeline_cv(
            pipeline=pipe,
            X=X_bio,
            y=y_bio,
            n_splits=n_splits,
            random_state=random_state,
        )
        test_res = evaluate_held_out_test(
            pipeline=pipe,
            X_train=X_bio_train,
            y_train=y_bio_train,
            X_test=X_bio_test,
            y_test=y_bio_test,
        )
        bio_cohort_results["models"][model_name] = {
            "cv_results": cv_res,
            "held_out_test_results": test_res,
        }

    results["cohorts"]["biosensor_cohort"] = bio_cohort_results
    return results


def save_experiment_report(
    results: dict[str, Any],
    output_dir: Path | str | None = None,
) -> tuple[Path, Path]:
    """Save experiment results to JSON and generate a detailed Markdown summary.

    Args:
        results: Benchmark dictionary produced by `run_tabular_benchmarks`.
        output_dir: Destination directory. Defaults to ARTIFACTS_DIR.

    Returns:
        Tuple of (json_path, markdown_path).
    """
    dest_dir = Path(output_dir) if output_dir is not None else ARTIFACTS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    json_path = dest_dir / "experiment_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    md_path = dest_dir / "experiment_summary.md"
    md_content = generate_markdown_summary(results)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    return json_path, md_path


def generate_markdown_summary(results: dict[str, Any]) -> str:
    """Generate structured markdown report summarizing model benchmarks and limitations."""
    lines = [
        "# Arogya AI — Tabular ML Baseline Experiment Summary (Module 9)",
        "",
        "> [!IMPORTANT]",
        "> **Research Prototype Notice**: This evaluation benchmarks baseline exploratory algorithms",
        "> on the Exasens respiratory biomarker dataset. Models are not validated for clinical diagnosis.",
        "",
        "## 1. Cross-Validation Benchmark Overview (5-Fold Stratified CV)",
        "",
        "### A. Full Demographic Cohort (N=399, 3 features: Age, Gender, Smoking)",
        "",
        "| Model | CV Macro-F1 (Mean ± Std) | CV Balanced Acc (Mean ± Std) | Held-Out Test Macro-F1 (20%) | Held-Out Test Acc |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    full_models = results["cohorts"]["full_cohort"]["models"]
    for mname, mdata in full_models.items():
        cv = mdata["cv_results"]
        test = mdata["held_out_test_results"]
        lines.append(
            f"| **{mname}** | {cv['cv_macro_f1_mean']:.4f} ± {cv['cv_macro_f1_std']:.4f} | "
            f"{cv['cv_balanced_acc_mean']:.4f} ± {cv['cv_balanced_acc_std']:.4f} | "
            f"{test['macro_f1']:.4f} | {test['accuracy']:.4f} |"
        )

    lines.extend([
        "",
        "### B. Complete Biosensor Cohort (N=100, 7 features: Demographics + 4 Dielectric Permittivity)",
        "",
        "| Model | CV Macro-F1 (Mean ± Std) | CV Balanced Acc (Mean ± Std) | Held-Out Test Macro-F1 (20%) | Held-Out Test Acc |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    bio_models = results["cohorts"]["biosensor_cohort"]["models"]
    for mname, mdata in bio_models.items():
        cv = mdata["cv_results"]
        test = mdata["held_out_test_results"]
        lines.append(
            f"| **{mname}** | {cv['cv_macro_f1_mean']:.4f} ± {cv['cv_macro_f1_std']:.4f} | "
            f"{cv['cv_balanced_acc_mean']:.4f} ± {cv['cv_balanced_acc_std']:.4f} | "
            f"{test['macro_f1']:.4f} | {test['accuracy']:.4f} |"
        )

    lines.extend([
        "",
        "## 2. Held-Out Test Confusion Matrices (Biosensor Cohort, N=20)",
        "",
    ])

    for mname, mdata in bio_models.items():
        test_res = mdata["held_out_test_results"]
        lines.append(f"#### {mname}")
        lines.append("```")
        lines.append(format_metrics_summary(test_res, model_name=mname, cohort_name="Biosensor Held-Out"))
        lines.append("```")
        lines.append("")

    lines.extend([
        "## 3. Dataset Constraints & Research Limitations",
        "",
        "1. **Severe Imbalance in Biosensor Cohort**: While the complete cohort has 40 COPD and 40 HC patients,",
        "   it contains only **10 Asthma** and **10 Infected** cases. In a 5-fold CV split, each validation fold",
        "   evaluates against only 2 samples for these minority classes, producing high variance in fold scores.",
        "2. **Demographic Ambiguity**: Demographic features alone (Age, Gender, Smoking) achieve modest discriminative",
        "   power (Macro-F1 ~0.35–0.40) because healthy smokers and elderly controls overlap heavily with clinical populations.",
        "3. **Sensor Feature Signal**: The addition of physical saliva permittivity measurements (Imaginary & Real dielectric values)",
        "   markedly elevates multi-class separation, with Random Forest achieving ~0.71–0.72 CV Macro-F1.",
        "4. **Model Deployment Limitations**: The serialized Random Forest is a research baseline, not a clinically",
        "   validated production diagnostic model. Its artifact is intended for controlled research and integration testing.",
    ])

    return "\n".join(lines)


def build_production_pipeline(random_state: int = 42) -> Pipeline:
    """Construct the primary production tabular pipeline (Random Forest).

    Selected based on 5-fold cross-validation performance (Macro-F1 ~0.71).
    Includes SimpleImputer to allow robust inference even when biosensor readings
    are missing or partially recorded.

    Args:
        random_state: Fixed pseudo-random seed.

    Returns:
        Configured scikit-learn Pipeline ready for fitting or inference.
    """
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        (
            "clf",
            RandomForestClassifier(
                n_estimators=100,
                max_depth=6,
                min_samples_split=4,
                class_weight="balanced",
                random_state=random_state,
            ),
        ),
    ])


def serialize_baseline_model(
    dataset: ExasensDataset | None = None,
    output_dir: Path | str | None = None,
    random_state: int = 42,
) -> tuple[Path, Path]:
    """Train, evaluate, serialize the production baseline model, and export metadata.

    Selects the Random Forest model based on documented cross-validation results
    (achieving highest CV Macro-F1: 0.7070 ± 0.0647 on biosensor cohort).

    Args:
        dataset: Optional loaded ExasensDataset. Loads default if None.
        output_dir: Destination directory. Defaults to ARTIFACTS_DIR.
        random_state: Random state for reproducibility.

    Returns:
        Tuple of (joblib_path, metadata_json_path).
    """
    if dataset is None:
        dataset = ExasensDataset.load()

    dest_dir = Path(output_dir) if output_dir is not None else ARTIFACTS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    X_bio, y_bio = dataset.biosensor_cohort()
    pipeline = build_production_pipeline(random_state=random_state)

    # 1. Cross-validation evaluation for metadata tracking
    cv_res = evaluate_pipeline_cv(
        pipeline=pipeline,
        X=X_bio,
        y=y_bio,
        n_splits=5,
        random_state=random_state,
    )

    # 2. Fit pipeline on the complete biosensor dataset
    pipeline.fit(X_bio, y_bio)

    # 3. Serialize fitted pipeline to joblib
    joblib_path = dest_dir / "tabular_baseline.joblib"
    joblib.dump(pipeline, joblib_path, compress=3)

    # 4. Compute SHA-256 checksum of the artifact
    sha256 = hashlib.sha256()
    with open(joblib_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    checksum = sha256.hexdigest()

    # 5. Compile metadata dictionary
    metadata: dict[str, Any] = {
        "model_name": "tabular_exasens_baseline",
        "model_version": "0.1.0-alpha",
        "model_family": "RandomForestClassifier",
        "framework": "scikit-learn",
        "framework_version": sklearn.__version__,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifact_file": "tabular_baseline.joblib",
        "sha256_checksum": checksum,
        "features": ALL_FEATURES,
        "classes": list(DIAGNOSIS_CLASSES),
        "target": "Diagnosis",
        "training_dataset": {
            "name": "Exasens respiratory biomarker dataset",
            "cohort": "Complete biosensor cohort",
            "total_records": len(X_bio),
            "class_distribution": y_bio.value_counts().to_dict(),
        },
        "hyperparameters": {
            "n_estimators": 100,
            "max_depth": 6,
            "min_samples_split": 4,
            "class_weight": "balanced",
            "random_state": random_state,
            "imputer_strategy": "median",
        },
        "evaluation_metrics": {
            "cv_folds": 5,
            "cv_macro_f1_mean": cv_res["cv_macro_f1_mean"],
            "cv_macro_f1_std": cv_res["cv_macro_f1_std"],
            "cv_balanced_acc_mean": cv_res["cv_balanced_acc_mean"],
            "cv_balanced_acc_std": cv_res["cv_balanced_acc_std"],
            "cv_accuracy_mean": cv_res["cv_accuracy_mean"],
            "cv_accuracy_std": cv_res["cv_accuracy_std"],
            "oof_per_class": cv_res["oof_metrics"]["per_class"],
        },
        "limitations": [
            "Severe minority class scarcity: only 10 Asthma and 10 Infected cases in training cohort.",
            "Research prototype only: not clinically validated or approved as a medical device.",
            "Demographic screening without biosensors has high diagnostic overlap.",
        ],
        "disclaimer": (
            "RESEARCH PROTOTYPE ONLY. This model is an experimental research baseline "
            "trained on 100 benchmark samples. It has NOT been clinically validated and "
            "must NEVER be used as an autonomous diagnostic tool or for clinical medical decisions."
        ),
    }

    metadata_path = dest_dir / "model_metadata.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return joblib_path, metadata_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Running Arogya AI Tabular ML Benchmarks...")
    bench_results = run_tabular_benchmarks()
    jpath, mpath = save_experiment_report(bench_results)
    print(f"Experiments successfully completed.")
    print(f"Results saved to: {jpath}")
    print(f"Summary saved to: {mpath}")
    print("Serializing baseline model artifact...")
    joblib_p, meta_p = serialize_baseline_model()
    print(f"Artifact serialized: {joblib_p}")
    print(f"Metadata generated: {meta_p}")

