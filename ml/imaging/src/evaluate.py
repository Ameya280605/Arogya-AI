"""Patient-level held-out evaluation for chest X-ray research.

IMPORTANT:
The pretrained model uses NIH ChestX-ray14 weights. This evaluation
does not establish independent validation because the evaluation
images may have appeared during model pretraining.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.model_selection import GroupShuffleSplit

from inference import ChestXrayInference


ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "ml" / "imaging" / "data"
IMAGE_DIR = DATA_DIR / "images"
CSV_PATH = DATA_DIR / "Data_Entry_2017_v2020.csv"
ARTIFACT_DIR = ROOT / "ml" / "imaging" / "artifacts"

SEED = 42
TEST_SIZE = 0.20
BATCH_SIZE = 16

ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("Loading dataset metadata...")

    df = pd.read_csv(CSV_PATH)

    available_images = {
        path.name for path in IMAGE_DIR.glob("*.png")
    }

    df = df[df["Image Index"].isin(available_images)].copy()
    df = df.sort_values("Image Index").reset_index(drop=True)

    if df.empty:
        raise RuntimeError("No dataset images were found.")

    if df["Image Index"].duplicated().any():
        raise RuntimeError("Duplicate image filenames found in CSV.")

    print(f"Available images: {len(df)}")
    print(f"Unique patients: {df['Patient ID'].nunique()}")

    # Split by patient, not by individual image.
    splitter = GroupShuffleSplit(
        n_splits=1,
        test_size=TEST_SIZE,
        random_state=SEED,
    )

    train_idx, test_idx = next(
        splitter.split(df, groups=df["Patient ID"])
    )

    train_df = df.iloc[train_idx].copy()
    test_df = df.iloc[test_idx].copy()

    train_patients = set(train_df["Patient ID"])
    test_patients = set(test_df["Patient ID"])

    assert train_patients.isdisjoint(test_patients)

    print(f"\nExcluded from evaluation: {len(train_df)} images")
    print(f"Held-out evaluation images: {len(test_df)}")
    print(f"Patients in excluded split: {len(train_patients)}")
    print(f"Patients in evaluation split: {len(test_patients)}")
    print("Patient overlap: 0")

    # Save the exact split so the experiment is reproducible.
    split_df = pd.concat(
        [
            train_df[["Image Index", "Patient ID"]].assign(
                split="excluded_from_evaluation"
            ),
            test_df[["Image Index", "Patient ID"]].assign(
                split="held_out_evaluation"
            ),
        ],
        ignore_index=True,
    )

    split_path = ARTIFACT_DIR / "evaluation_split.csv"
    split_df.to_csv(split_path, index=False)

    print("\nLoading pretrained model...")
    pipeline = ChestXrayInference()
    labels = pipeline.labels

    # Build multi-label ground truth using the model's label order.
    findings = (
        test_df["Finding Labels"]
        .fillna("")
        .str.split("|")
    )

    y_true = np.array(
        [
            [int(label in image_findings) for label in labels]
            for image_findings in findings
        ],
        dtype=np.int32,
    )

    image_paths = [
        IMAGE_DIR / name for name in test_df["Image Index"]
    ]

    all_scores = []

    print("\nRunning inference...")

    for start in range(0, len(image_paths), BATCH_SIZE):
        batch_paths = image_paths[start : start + BATCH_SIZE]

        tensors = [
            pipeline.preprocess(path)
            for path in batch_paths
        ]

        batch_tensor = torch.cat(tensors, dim=0)

        with torch.inference_mode():
            output = pipeline.model(batch_tensor.to(pipeline.device))

        if output.ndim != 2 or output.shape[1] < len(labels):
            raise RuntimeError(
                f"Unexpected model output shape: {tuple(output.shape)}"
            )

        scores = output[:, : len(labels)].cpu().numpy()

        if not np.isfinite(scores).all():
            raise RuntimeError("Non-finite model scores detected.")

        all_scores.append(scores)

        completed = min(start + len(batch_paths), len(image_paths))
        print(f"Processed {completed}/{len(image_paths)} images")

    y_score = np.concatenate(all_scores, axis=0)

    if y_score.shape != y_true.shape:
        raise RuntimeError(
            f"Score/label shape mismatch: "
            f"{y_score.shape} versus {y_true.shape}"
        )

    results = []

    print("\nPer-label evaluation:")
    print("-" * 88)
    print(
        f"{'Label':<22} {'Positive':>9} {'Negative':>9} "
        f"{'AUROC':>12} {'Avg Precision':>16}"
    )
    print("-" * 88)

    for i, label in enumerate(labels):
        truth = y_true[:, i]
        score = y_score[:, i]

        positives = int(truth.sum())
        negatives = int(len(truth) - positives)

        # Both metrics require positive and negative examples
        # for a meaningful binary classification evaluation.
        if positives == 0 or negatives == 0:
            auroc = None
            avg_precision = None
        else:
            auroc = float(roc_auc_score(truth, score))
            avg_precision = float(
                average_precision_score(truth, score)
            )

        results.append(
            {
                "label": label,
                "evaluation_images": int(len(truth)),
                "positive_count": positives,
                "negative_count": negatives,
                "auroc": auroc,
                "average_precision": avg_precision,
            }
        )

        auroc_text = "N/A" if auroc is None else f"{auroc:.4f}"
        ap_text = (
            "N/A"
            if avg_precision is None
            else f"{avg_precision:.4f}"
        )

        print(
            f"{label:<22} {positives:>9} {negatives:>9} "
            f"{auroc_text:>12} {ap_text:>16}"
        )

    metrics_path = ARTIFACT_DIR / "evaluation_metrics.csv"
    pd.DataFrame(results).to_csv(metrics_path, index=False)

    metadata = {
        "model_weights": pipeline.MODEL_WEIGHTS,
        "model_library_version": getattr(
            __import__("torchxrayvision"),
            "__version__",
            "unknown",
        ),
        "random_seed": SEED,
        "test_size": TEST_SIZE,
        "batch_size": BATCH_SIZE,
        "available_images": int(len(df)),
        "available_patients": int(df["Patient ID"].nunique()),
        "evaluation_images": int(len(test_df)),
        "evaluation_patients": int(len(test_patients)),
        "patient_overlap_between_splits": 0,
        "labels": labels,
        "score_interpretation": (
            "Raw model scores; not calibrated probabilities "
            "and not diagnoses."
        ),
        "validation_limitation": (
            "The model was pretrained on NIH ChestX-ray14. "
            "Evaluation images come from the same dataset, and "
            "overlap with model pretraining cannot be ruled out. "
            "This is not independent external validation."
        ),
        "research_only": True,
    }

    metadata_path = ARTIFACT_DIR / "evaluation_metadata.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\nEvaluation files saved:")
    print(f"  Split:    {split_path}")
    print(f"  Metrics:  {metrics_path}")
    print(f"  Metadata: {metadata_path}")

    print("\nRESEARCH ONLY — NOT FOR CLINICAL DIAGNOSIS.")


if __name__ == "__main__":
    main()