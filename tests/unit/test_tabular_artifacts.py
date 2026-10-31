"""Arogya AI - Unit Tests for Tabular Model Artifact Serialization & Integrity.

Module 9: Tabular ML Baseline Classification.
Tests artifact loading, SHA-256 checksum verification, metadata validation,
prediction output schemas, probability calibration, and fallback imputation.
"""

import hashlib
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.pipeline import Pipeline

from ml.tabular.src.dataset import ALL_FEATURES, DIAGNOSIS_CLASSES, ExasensDataset
from ml.tabular.src.train import ARTIFACTS_DIR

MODEL_CARDS_DIR = Path(__file__).resolve().parent.parent.parent / "ml" / "model_cards"


@pytest.mark.unit
def test_joblib_artifact_exists_and_is_pipeline():
    """Verify that tabular_baseline.joblib exists and loads as a valid scikit-learn Pipeline."""
    joblib_path = ARTIFACTS_DIR / "tabular_baseline.joblib"
    assert joblib_path.exists(), f"Model artifact missing at {joblib_path}"
    assert joblib_path.stat().st_size > 0

    pipeline = joblib.load(joblib_path)
    assert isinstance(pipeline, Pipeline), "Loaded artifact is not a scikit-learn Pipeline"
    assert "imputer" in pipeline.named_steps
    assert "clf" in pipeline.named_steps
    assert set(pipeline.classes_) == set(DIAGNOSIS_CLASSES)


@pytest.mark.unit
def test_model_metadata_schema_and_contents():
    """Verify model_metadata.json structure, required fields, and non-diagnostic disclaimers."""
    meta_path = ARTIFACTS_DIR / "model_metadata.json"
    assert meta_path.exists(), f"Metadata JSON missing at {meta_path}"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    # Core identity
    assert meta["model_name"] == "tabular_exasens_baseline"
    assert meta["model_version"] == "0.1.0-alpha"
    assert meta["model_family"] == "RandomForestClassifier"
    assert meta["artifact_file"] == "tabular_baseline.joblib"

    # Cryptographic integrity
    assert "sha256_checksum" in meta
    assert len(meta["sha256_checksum"]) == 64

    # Feature and class contracts
    assert meta["features"] == ALL_FEATURES
    assert set(meta["classes"]) == set(DIAGNOSIS_CLASSES)
    assert meta["target"] == "Diagnosis"

    # Evaluation metrics
    metrics = meta["evaluation_metrics"]
    assert metrics["cv_folds"] == 5
    assert 0.0 <= metrics["cv_macro_f1_mean"] <= 1.0
    assert 0.0 <= metrics["cv_balanced_acc_mean"] <= 1.0
    assert 0.0 <= metrics["cv_accuracy_mean"] <= 1.0

    # Safety disclaimer
    assert "RESEARCH PROTOTYPE ONLY" in meta["disclaimer"]


@pytest.mark.unit
def test_sha256_checksum_matches_actual_artifact():
    """Cryptographic verification: Actual file SHA-256 must match recorded metadata."""
    joblib_path = ARTIFACTS_DIR / "tabular_baseline.joblib"
    meta_path = ARTIFACTS_DIR / "model_metadata.json"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    expected_hash = meta["sha256_checksum"]

    sha256 = hashlib.sha256()
    with open(joblib_path, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    actual_hash = sha256.hexdigest()

    assert actual_hash == expected_hash, (
        f"Artifact SHA-256 checksum mismatch! Actual: {actual_hash}, Expected: {expected_hash}"
    )


@pytest.mark.unit
def test_prediction_output_and_probabilities():
    """Verify that loaded pipeline outputs valid class predictions and normalized probabilities."""
    joblib_path = ARTIFACTS_DIR / "tabular_baseline.joblib"
    pipeline = joblib.load(joblib_path)

    # Synthetic complete patient record
    sample_data = pd.DataFrame([{
        "Age": 65,
        "Gender": 1,
        "Smoking": 2,
        "Imaginary_Min": -320.61,
        "Imaginary_Avg": -300.56,
        "Real_Min": -495.26,
        "Real_Avg": -464.17,
    }])[ALL_FEATURES]

    pred = pipeline.predict(sample_data)[0]
    probs = pipeline.predict_proba(sample_data)[0]

    assert pred in DIAGNOSIS_CLASSES
    assert len(probs) == len(DIAGNOSIS_CLASSES)
    assert pytest.approx(float(probs.sum()), abs=1e-5) == 1.0
    assert all(0.0 <= p <= 1.0 for p in probs)


@pytest.mark.unit
def test_prediction_fallback_with_missing_biosensors():
    """Verify that pipeline handles missing/NaN biosensor measurements via imputation."""
    joblib_path = ARTIFACTS_DIR / "tabular_baseline.joblib"
    pipeline = joblib.load(joblib_path)

    # Patient record lacking saliva dielectric sensor readings
    sample_demographic_only = pd.DataFrame([{
        "Age": 50,
        "Gender": 0,
        "Smoking": 1,
        "Imaginary_Min": np.nan,
        "Imaginary_Avg": np.nan,
        "Real_Min": np.nan,
        "Real_Avg": np.nan,
    }])[ALL_FEATURES]

    pred = pipeline.predict(sample_demographic_only)[0]
    probs = pipeline.predict_proba(sample_demographic_only)[0]

    assert pred in DIAGNOSIS_CLASSES
    assert pytest.approx(float(probs.sum()), abs=1e-5) == 1.0


@pytest.mark.unit
def test_model_card_documentation_exists():
    """Verify that the formal research model card exists and contains governance sections."""
    card_path = MODEL_CARDS_DIR / "tabular_exasens_baseline.md"
    assert card_path.exists(), f"Model card missing at {card_path}"

    content = card_path.read_text(encoding="utf-8")
    assert "NON-DIAGNOSTIC RESEARCH PROTOTYPE DISCLAIMER" in content
    assert "Model Details" in content
    assert "Intended Use & Non-Goals" in content
    assert "Training & Validation Data" in content
    assert "Quantitative Evaluation & Metrics" in content
    assert "Known Limitations & Failure Modes" in content

