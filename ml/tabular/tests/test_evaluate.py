import numpy as np
import pytest

from ml.tabular.src.evaluate import compute_classification_metrics


LABELS = ("HC", "Asthma", "Infected", "COPD")


def test_classification_metrics_include_all_classes():
    y_true = ["HC", "Asthma", "Infected", "COPD"]
    y_pred = ["HC", "Asthma", "COPD", "COPD"]

    metrics = compute_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        labels=LABELS,
    )

    assert metrics["accuracy"] == pytest.approx(0.75)
    assert metrics["macro_f1"] >= 0.0
    assert metrics["balanced_accuracy"] >= 0.0
    assert metrics["labels"] == list(LABELS)
    assert len(metrics["confusion_matrix"]) == 4
    assert set(metrics["per_class"]) == set(LABELS)


def test_per_class_metrics_include_sensitivity_and_specificity():
    y_true = ["HC", "HC", "Asthma", "Asthma"]
    y_pred = ["HC", "Asthma", "Asthma", "Asthma"]

    metrics = compute_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        labels=LABELS,
    )

    assert metrics["per_class"]["HC"]["sensitivity"] == pytest.approx(0.5)
    assert metrics["per_class"]["Asthma"]["sensitivity"] == pytest.approx(1.0)
    assert "specificity" in metrics["per_class"]["HC"]
    assert "false_positive" in metrics["per_class"]["HC"]


def test_probability_metrics_are_calculated():
    y_true = ["HC", "Asthma", "Infected", "COPD"]
    y_prob = np.array([
        [0.85, 0.05, 0.05, 0.05],
        [0.05, 0.85, 0.05, 0.05],
        [0.05, 0.05, 0.85, 0.05],
        [0.05, 0.05, 0.05, 0.85],
    ])
    y_pred = [LABELS[i] for i in np.argmax(y_prob, axis=1)]

    metrics = compute_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
        labels=LABELS,
    )

    assert "log_loss" in metrics
    assert "brier_score" in metrics
    assert np.isfinite(metrics["log_loss"])
    assert np.isfinite(metrics["brier_score"])


def test_missing_class_in_true_labels_is_handled():
    y_true = ["HC", "HC", "COPD", "COPD"]
    y_pred = ["HC", "Asthma", "COPD", "COPD"]

    metrics = compute_classification_metrics(
        y_true=y_true,
        y_pred=y_pred,
        labels=LABELS,
    )

    assert metrics["per_class"]["Infected"]["support"] == 0
    assert metrics["per_class"]["Infected"]["recall"] == 0.0
    assert len(metrics["confusion_matrix"]) == 4
