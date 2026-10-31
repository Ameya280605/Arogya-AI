"""Arogya AI - Unit Tests for Standalone Tabular Predictor.

Module 9: Tabular ML Baseline Classification.
Tests input schema validation, boundary conditions, batch inference,
SHA-256 integrity enforcement, fallback imputation, and CLI execution.
"""

import json
import subprocess
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.tabular.src.dataset import ALL_FEATURES, BIOSENSOR_FEATURES, DIAGNOSIS_CLASSES
from ml.tabular.src.predictor import PredictionResult, TabularPredictor


@pytest.fixture
def predictor() -> TabularPredictor:
    """Fixture providing initialized and checksum-verified TabularPredictor."""
    return TabularPredictor()


@pytest.mark.unit
def test_predict_single_complete_record(predictor: TabularPredictor):
    """Verify single prediction with complete demographic and biosensor features."""
    input_data = {
        "Age": 65,
        "Gender": 1,
        "Smoking": 2,
        "Imaginary_Min": -320.61,
        "Imaginary_Avg": -300.56,
        "Real_Min": -495.26,
        "Real_Avg": -464.17,
    }

    result = predictor.predict_single(input_data)

    assert isinstance(result, PredictionResult)
    assert result.predicted_class in DIAGNOSIS_CLASSES
    assert set(result.class_probabilities.keys()) == set(DIAGNOSIS_CLASSES)
    assert pytest.approx(sum(result.class_probabilities.values()), abs=1e-3) == 1.0
    assert result.imputed_features == []
    assert result.is_research_prototype is True
    assert "RESEARCH PROTOTYPE ONLY" in result.disclaimer


@pytest.mark.unit
def test_predict_single_with_fallback_imputation(predictor: TabularPredictor):
    """Verify inference when dielectric sensor readings are absent (demographics only)."""
    demographic_only = {
        "Age": 55,
        "Gender": 0,
        "Smoking": 1,
    }

    result = predictor.predict_single(demographic_only)

    assert result.predicted_class in DIAGNOSIS_CLASSES
    assert set(result.imputed_features) == set(BIOSENSOR_FEATURES)
    assert pytest.approx(sum(result.class_probabilities.values()), abs=1e-3) == 1.0


@pytest.mark.unit
def test_predict_batch_dict_and_dataframe(predictor: TabularPredictor):
    """Verify batch prediction across sequences and DataFrames."""
    records = [
        {"Age": 70, "Gender": 1, "Smoking": 3, "Imaginary_Min": -325.0, "Imaginary_Avg": -310.0, "Real_Min": -480.0, "Real_Avg": -470.0},
        {"Age": 35, "Gender": 0, "Smoking": 1},
        {"Age": 45, "Gender": 1, "Smoking": 2, "Imaginary_Min": -315.0, "Imaginary_Avg": -295.0, "Real_Min": -470.0, "Real_Avg": -460.0},
    ]

    # Batch prediction from list of dicts
    batch_results = predictor.predict_batch(records)
    assert len(batch_results) == 3
    assert all(r.predicted_class in DIAGNOSIS_CLASSES for r in batch_results)
    assert batch_results[1].imputed_features == BIOSENSOR_FEATURES

    # Batch prediction from DataFrame
    df = pd.DataFrame(records)
    df_results = predictor.predict_batch(df)
    assert len(df_results) == 3


@pytest.mark.unit
@pytest.mark.parametrize(
    "invalid_input,expected_error",
    [
        ({"Gender": 1, "Smoking": 1}, "Missing mandatory demographic feature 'Age'"),
        ({"Age": "invalid", "Gender": 1, "Smoking": 1}, "Age must be an integer"),
        ({"Age": 150, "Gender": 1, "Smoking": 1}, "outside physiological range"),
        ({"Age": -1, "Gender": 1, "Smoking": 1}, "outside physiological range"),
        ({"Age": 45, "Gender": "alien", "Smoking": 1}, "Invalid Gender"),
        ({"Age": 45, "Gender": 3, "Smoking": 1}, r"Gender must be 0 \(Female\) or 1 \(Male\)"),
        ({"Age": 45, "Gender": 1, "Smoking": 5}, "Smoking status must be in"),
        ({"Age": 45, "Gender": 1, "Smoking": 1, "Imaginary_Min": "corrupt"}, "must be numeric float"),
    ],
)
def test_input_validation_errors(invalid_input: dict, expected_error: str):
    """Verify that malformed, unphysiological, or missing inputs raise informative ValueErrors."""
    with pytest.raises(ValueError, match=expected_error):
        TabularPredictor.validate_input_dict(invalid_input)


@pytest.mark.unit
def test_checksum_failure_detection(tmp_path: Path):
    """Verify that tampering with artifact or metadata triggers checksum failure."""
    real_predictor = TabularPredictor()
    real_meta_path = real_predictor.metadata_path
    real_model_path = real_predictor.model_path

    # Create dummy metadata with tampered hash
    tampered_meta = json.loads(real_meta_path.read_text(encoding="utf-8"))
    tampered_meta["sha256_checksum"] = "0000000000000000000000000000000000000000000000000000000000000000"

    tampered_meta_path = tmp_path / "tampered_metadata.json"
    tampered_meta_path.write_text(json.dumps(tampered_meta), encoding="utf-8")

    with pytest.raises(ValueError, match="Artifact integrity compromised! Checksum mismatch"):
        TabularPredictor(
            model_path=real_model_path,
            metadata_path=tampered_meta_path,
            verify_checksum=True,
        )


@pytest.mark.unit
def test_cli_execution_valid_output():
    """Verify CLI interface execution produces valid JSON output and expected keys."""
    cmd = [
        sys.executable,
        "-m",
        "ml.tabular.src.predictor",
        "--age",
        "68",
        "--gender",
        "1",
        "--smoking",
        "2",
        "--imaginary-min",
        "-323.0",
        "--imaginary-avg",
        "-314.5",
        "--real-min",
        "-502.4",
        "--real-avg",
        "-467.8",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    parsed = json.loads(result.stdout)

    assert "predicted_class" in parsed
    assert parsed["predicted_class"] in DIAGNOSIS_CLASSES
    assert "class_probabilities" in parsed
    assert "is_research_prototype" in parsed
    assert parsed["is_research_prototype"] is True
    assert "disclaimer" in parsed
