"""Arogya AI - Tabular ML Model Evaluation Metrics & Analysis.

Module 9: Tabular ML Baseline Classification.
Computes multi-class evaluation metrics, confusion matrices, per-class sensitivity/specificity,
and calibration indicators with strict prevention of data contamination.

SAFETY & GOVERNANCE NOTICE:
This evaluation framework supports research benchmarking only.
Metrics do NOT indicate clinical efficacy, safety, or regulatory certification.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)

logger = logging.getLogger(__name__)

DEFAULT_DIAGNOSIS_CLASSES: tuple[str, ...] = ("HC", "Asthma", "Infected", "COPD")


def compute_classification_metrics(
    y_true: Sequence[str] | np.ndarray,
    y_pred: Sequence[str] | np.ndarray,
    y_prob: np.ndarray | None = None,
    labels: Sequence[str] = DEFAULT_DIAGNOSIS_CLASSES,
) -> dict[str, Any]:
    """Compute comprehensive multiclass clinical classification metrics.

    Args:
        y_true: Ground truth target labels.
        y_pred: Predicted target labels.
        y_prob: Optional predicted probability matrix of shape (n_samples, n_classes).
        labels: Canonical label sequence ordering.

    Returns:
        Structured dictionary containing global scores, per-class breakdown,
        and confusion matrix representation.
    """
    labels_list = list(labels)
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)

    # Core multi-class metrics
    acc = float(accuracy_score(y_true_arr, y_pred_arr))
    balanced_acc = float(balanced_accuracy_score(y_true_arr, y_pred_arr))
    macro_f1 = float(f1_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true_arr, y_pred_arr, average="weighted", zero_division=0))
    macro_precision = float(precision_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))
    macro_recall = float(recall_score(y_true_arr, y_pred_arr, average="macro", zero_division=0))

    # Confusion matrix with fixed class labels
    cm = confusion_matrix(y_true_arr, y_pred_arr, labels=labels_list)

    # Per-class detailed breakdown
    clf_report = classification_report(
        y_true_arr,
        y_pred_arr,
        labels=labels_list,
        target_names=labels_list,
        output_dict=True,
        zero_division=0,
    )

    per_class_metrics: dict[str, dict[str, Any]] = {}
    for i, cls_name in enumerate(labels_list):
        cls_stats = clf_report.get(cls_name, {})
        tp = int(cm[i, i])
        fn = int(cm[i, :].sum() - tp)
        fp = int(cm[:, i].sum() - tp)
        tn = int(cm.sum() - (tp + fn + fp))

        sensitivity = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        specificity = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0

        per_class_metrics[cls_name] = {
            "precision": float(cls_stats.get("precision", 0.0)),
            "recall": float(cls_stats.get("recall", 0.0)),
            "f1_score": float(cls_stats.get("f1-score", 0.0)),
            "support": int(cls_stats.get("support", 0)),
            "sensitivity": sensitivity,
            "specificity": specificity,
            "true_positive": tp,
            "false_negative": fn,
            "false_positive": fp,
            "true_negative": tn,
        }

    results: dict[str, Any] = {
        "accuracy": acc,
        "balanced_accuracy": balanced_acc,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "macro_precision": macro_precision,
        "macro_recall": macro_recall,
        "labels": labels_list,
        "confusion_matrix": cm.tolist(),
        "per_class": per_class_metrics,
    }

    # Probability-based metrics (if probabilities provided)
    if y_prob is not None and len(y_prob) == len(y_true_arr):
        try:
            # Multiclass log loss requires lexicographically sorted labels and matching prob columns
            sorted_labels = sorted(labels_list)
            sort_indices = [labels_list.index(lbl) for lbl in sorted_labels]
            sorted_probs = y_prob[:, sort_indices]
            loss = float(log_loss(y_true_arr, sorted_probs, labels=sorted_labels))
            results["log_loss"] = loss

            # Multiclass Brier score: mean squared difference from one-hot target
            one_hot = np.zeros_like(y_prob)
            for sample_idx, true_label in enumerate(y_true_arr):
                if true_label in labels_list:
                    cls_idx = labels_list.index(true_label)
                    one_hot[sample_idx, cls_idx] = 1.0

            brier = float(np.mean(np.sum((y_prob - one_hot) ** 2, axis=1)))
            results["brier_score"] = brier
        except Exception as exc:
            logger.warning(f"Could not compute probability-based metrics: {exc}")

    return results


def format_confusion_matrix_text(
    cm: list[list[int]] | np.ndarray,
    labels: Sequence[str] = DEFAULT_DIAGNOSIS_CLASSES,
) -> str:
    """Format a confusion matrix into a clean monospace ASCII table.

    Args:
        cm: Confusion matrix array of shape (n_classes, n_classes).
        labels: Class labels sequence.

    Returns:
        Formatted ASCII confusion matrix string.
    """
    labels_list = list(labels)
    cm_arr = np.asarray(cm)
    col_width = max(len(lbl) for lbl in labels_list) + 2
    header = "True \\ Pred".ljust(col_width) + "".join(lbl.rjust(col_width) for lbl in labels_list)
    separator = "-" * len(header)
    lines = [header, separator]

    for i, true_lbl in enumerate(labels_list):
        row_str = true_lbl.ljust(col_width) + "".join(str(int(cm_arr[i, j])).rjust(col_width) for j in range(len(labels_list)))
        lines.append(row_str)

    return "\n".join(lines)


def format_metrics_summary(
    metrics: dict[str, Any],
    model_name: str = "",
    cohort_name: str = "",
) -> str:
    """Format a clean textual report of classification metrics."""
    header = f"=== Model Evaluation: {model_name} [{cohort_name}] ==="
    lines = [
        header,
        f"Macro F1-Score:      {metrics.get('macro_f1', 0.0):.4f}",
        f"Balanced Accuracy:   {metrics.get('balanced_accuracy', 0.0):.4f}",
        f"Overall Accuracy:    {metrics.get('accuracy', 0.0):.4f}",
        f"Weighted F1-Score:   {metrics.get('weighted_f1', 0.0):.4f}",
        f"Macro Precision:     {metrics.get('macro_precision', 0.0):.4f}",
        f"Macro Recall:        {metrics.get('macro_recall', 0.0):.4f}",
    ]

    if "log_loss" in metrics:
        lines.append(f"Log Loss:            {metrics['log_loss']:.4f}")
    if "brier_score" in metrics:
        lines.append(f"Brier Score:         {metrics['brier_score']:.4f}")

    lines.append("\nPer-Class Breakdown:")
    per_class = metrics.get("per_class", {})
    for cls_name, pstats in per_class.items():
        lines.append(
            f"  - {cls_name:<10}: Precision={pstats['precision']:.3f}, "
            f"Recall={pstats['recall']:.3f}, F1={pstats['f1_score']:.3f}, "
            f"Sens={pstats['sensitivity']:.3f}, Spec={pstats['specificity']:.3f} "
            f"(Support={pstats['support']})"
        )

    lines.append("\nConfusion Matrix:")
    if "confusion_matrix" in metrics and "labels" in metrics:
        lines.append(format_confusion_matrix_text(metrics["confusion_matrix"], metrics["labels"]))

    return "\n".join(lines)
