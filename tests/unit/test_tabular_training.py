"""Arogya AI - Unit Tests for Tabular Model Training, Metrics & Reproducibility.

Module 9: Tabular ML Baseline Classification.
Tests multi-class evaluation metrics, confusion matrix formatting, pipeline construction,
stratified cross-validation leakage safeguards, and training reproducibility.
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.tabular.src.dataset import DIAGNOSIS_CLASSES, ExasensDataset
from ml.tabular.src.evaluate import (
    compute_classification_metrics,
    format_confusion_matrix_text,
    format_metrics_summary,
)
from ml.tabular.src.train import (
    ARTIFACTS_DIR,
    build_model_pipelines,
    evaluate_held_out_test,
    evaluate_pipeline_cv,
    run_tabular_benchmarks,
    save_experiment_report,
)


@pytest.mark.unit
def test_compute_classification_metrics_exact_values():
    """Verify multiclass metrics calculation against known reference predictions."""
    y_true = ["HC", "Asthma", "Infected", "COPD"]
    y_pred = ["HC", "Asthma", "Infected", "COPD"]

    metrics = compute_classification_metrics(y_true, y_pred, labels=DIAGNOSIS_CLASSES)

    assert metrics["accuracy"] == 1.0
    assert metrics["balanced_accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["weighted_f1"] == 1.0
    assert metrics["macro_precision"] == 1.0
    assert metrics["macro_recall"] == 1.0

    cm = np.array(metrics["confusion_matrix"])
    assert np.array_equal(cm, np.eye(4, dtype=int))

    # All per-class sensitivity & specificity must be 1.0
    for cls in DIAGNOSIS_CLASSES:
        pstats = metrics["per_class"][cls]
        assert pstats["precision"] == 1.0
        assert pstats["recall"] == 1.0
        assert pstats["f1_score"] == 1.0
        assert pstats["sensitivity"] == 1.0
        assert pstats["specificity"] == 1.0


@pytest.mark.unit
def test_compute_classification_metrics_with_probabilities():
    """Verify log-loss and Brier score calculation with predicted probabilities."""
    y_true = ["HC", "COPD"]
    y_pred = ["HC", "COPD"]
    # Probabilities aligned with labels ['HC', 'Asthma', 'Infected', 'COPD']
    y_prob = np.array([
        [0.85, 0.05, 0.05, 0.05],  # Sample 0: true is HC
        [0.05, 0.05, 0.05, 0.85],  # Sample 1: true is COPD
    ])

    metrics = compute_classification_metrics(
        y_true, y_pred, y_prob=y_prob, labels=DIAGNOSIS_CLASSES
    )

    assert "log_loss" in metrics
    assert "brier_score" in metrics
    assert metrics["log_loss"] > 0.0
    assert metrics["brier_score"] > 0.0
    assert metrics["accuracy"] == 1.0


@pytest.mark.unit
def test_format_confusion_matrix_and_summary():
    """Verify ASCII table and summary generation for confusion matrices."""
    y_true = ["HC", "Asthma", "Infected", "COPD"]
    y_pred = ["HC", "HC", "Infected", "COPD"]
    metrics = compute_classification_metrics(y_true, y_pred, labels=DIAGNOSIS_CLASSES)

    text_cm = format_confusion_matrix_text(metrics["confusion_matrix"], DIAGNOSIS_CLASSES)
    assert "True \\ Pred" in text_cm
    for cls in DIAGNOSIS_CLASSES:
        assert cls in text_cm

    summary = format_metrics_summary(metrics, model_name="TestModel", cohort_name="TestCohort")
    assert "TestModel" in summary
    assert "Macro F1-Score" in summary
    assert "Confusion Matrix:" in summary


@pytest.mark.unit
def test_build_model_pipelines_structure():
    """Verify pipeline components and data leakage encapsulation."""
    pipelines = build_model_pipelines(random_state=42)

    assert set(pipelines.keys()) == {"LogisticRegression", "RandomForest", "SVC"}

    # StandardScaler must be present in LogisticRegression and SVC pipelines
    assert "scaler" in pipelines["LogisticRegression"].named_steps
    assert "scaler" in pipelines["SVC"].named_steps
    assert "clf" in pipelines["RandomForest"].named_steps


@pytest.mark.unit
def test_cv_leakage_and_structure(tmp_path: Path):
    """Verify 5-fold CV executes with valid out-of-fold metrics and no NaN values."""
    dataset = ExasensDataset.load()
    X_bio, y_bio = dataset.biosensor_cohort()

    pipelines = build_model_pipelines(random_state=42)
    rf_pipe = pipelines["RandomForest"]

    cv_res = evaluate_pipeline_cv(rf_pipe, X_bio, y_bio, n_splits=5, random_state=42)

    assert cv_res["cv_folds"] == 5
    assert len(cv_res["fold_scores"]) == 5

    assert 0.0 <= cv_res["cv_macro_f1_mean"] <= 1.0
    assert 0.0 <= cv_res["cv_balanced_acc_mean"] <= 1.0

    # Out-of-fold metrics must cover all 100 samples
    oof = cv_res["oof_metrics"]
    cm = np.array(oof["confusion_matrix"])
    assert cm.sum() == 100


@pytest.mark.unit
def test_reproducibility_of_held_out_evaluation():
    """Verify exact reproducibility across repeated runs with fixed seed."""
    dataset = ExasensDataset.load()
    X_tr, X_te, y_tr, y_te = dataset.split_biosensor_cohort(test_size=0.2, random_state=42)

    pipelines = build_model_pipelines(random_state=42)
    lr_pipe1 = pipelines["LogisticRegression"]
    res1 = evaluate_held_out_test(lr_pipe1, X_tr, y_tr, X_te, y_te)

    lr_pipe2 = build_model_pipelines(random_state=42)["LogisticRegression"]
    res2 = evaluate_held_out_test(lr_pipe2, X_tr, y_tr, X_te, y_te)

    assert res1["macro_f1"] == pytest.approx(res2["macro_f1"], rel=1e-6)
    assert res1["accuracy"] == pytest.approx(res2["accuracy"], rel=1e-6)
    assert res1["confusion_matrix"] == res2["confusion_matrix"]


@pytest.mark.unit
def test_experiment_report_artifacts_generated():
    """Verify that experiment_results.json and experiment_summary.md are created and valid."""
    assert ARTIFACTS_DIR.exists()
    json_path = ARTIFACTS_DIR / "experiment_results.json"
    md_path = ARTIFACTS_DIR / "experiment_summary.md"

    assert json_path.exists(), f"Missing {json_path}"
    assert md_path.exists(), f"Missing {md_path}"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "cohorts" in data
    assert "full_cohort" in data["cohorts"]
    assert "biosensor_cohort" in data["cohorts"]

    for cohort_key in ("full_cohort", "biosensor_cohort"):
        cohort = data["cohorts"][cohort_key]
        assert "LogisticRegression" in cohort["models"]
        assert "RandomForest" in cohort["models"]
        assert "SVC" in cohort["models"]

