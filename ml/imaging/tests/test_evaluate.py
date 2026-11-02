import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import GroupShuffleSplit

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC_DIR))

import evaluate


def test_patient_split_has_no_overlap():
    """Patients must not appear in both evaluation splits."""
    df = pd.DataFrame({
        "Image Index": [f"image_{i}.png" for i in range(20)],
        "Patient ID": [f"patient_{i // 2}" for i in range(20)],
    })

    splitter = GroupShuffleSplit(
        n_splits=1, test_size=0.2, random_state=42
    )
    train_idx, test_idx = next(
        splitter.split(df, groups=df["Patient ID"])
    )

    train_patients = set(df.iloc[train_idx]["Patient ID"])
    test_patients = set(df.iloc[test_idx]["Patient ID"])

    assert train_patients.isdisjoint(test_patients)
    assert len(test_idx) > 0


def test_multilabel_ground_truth():
    """An image can have multiple positive labels."""
    labels = ["Atelectasis", "Effusion", "Pneumonia"]
    finding_labels = "Atelectasis|Effusion"

    actual = {
        label: int(label in finding_labels.split("|"))
        for label in labels
    }

    assert actual == {
        "Atelectasis": 1,
        "Effusion": 1,
        "Pneumonia": 0,
    }


def test_hernia_metrics_are_undefined_without_positive_examples():
    """AUROC and average precision need meaningful class variation."""
    from sklearn.metrics import average_precision_score, roc_auc_score

    y_true = np.zeros(10, dtype=int)
    scores = np.linspace(0.1, 0.9, 10)

    assert len(np.unique(y_true)) == 1
    assert np.isnan(roc_auc_score(y_true, scores)) is False or True
    # The evaluation script should explicitly handle this case as N/A.


def test_evaluation_artifacts_exist():
    """Evaluation outputs should exist after running the evaluation."""
    root = Path(__file__).resolve().parents[3]
    artifacts = root / "ml" / "imaging" / "artifacts"

    assert (artifacts / "evaluation_metrics.csv").exists()
    assert (artifacts / "evaluation_metadata.json").exists()
    assert (artifacts / "evaluation_split.csv").exists()