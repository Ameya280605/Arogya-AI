"""Arogya AI - Tabular Machine Learning Research Package.

Module 9: Tabular ML Baseline Classification & Biosensor Risk Modeling.
Non-diagnostic research prototype.
"""

from ml.tabular.src.dataset import (
    ALL_FEATURES,
    BIOSENSOR_FEATURES,
    DEFAULT_DATASET_PATH,
    DEMOGRAPHIC_FEATURES,
    DIAGNOSIS_CLASSES,
    ID_COLUMN,
    TARGET_COLUMN,
    ExasensDataset,
    clean_exasens_data,
    get_complete_biosensor_cohort,
    get_full_cohort,
    load_exasens_raw,
    split_cohort,
    validate_exasens_dataframe,
)
from ml.tabular.src.evaluate import (
    compute_classification_metrics,
    format_confusion_matrix_text,
    format_metrics_summary,
)
from ml.tabular.src.predictor import (
    RESEARCH_DISCLAIMER,
    PredictionResult,
    TabularPredictor,
)
from ml.tabular.src.train import (
    build_model_pipelines,
    build_production_pipeline,
    evaluate_held_out_test,
    evaluate_pipeline_cv,
    run_tabular_benchmarks,
    save_experiment_report,
    serialize_baseline_model,
)

__all__ = [
    "ALL_FEATURES",
    "BIOSENSOR_FEATURES",
    "DEFAULT_DATASET_PATH",
    "DEMOGRAPHIC_FEATURES",
    "DIAGNOSIS_CLASSES",
    "ID_COLUMN",
    "TARGET_COLUMN",
    "ExasensDataset",
    "clean_exasens_data",
    "get_complete_biosensor_cohort",
    "get_full_cohort",
    "load_exasens_raw",
    "split_cohort",
    "validate_exasens_dataframe",
    "compute_classification_metrics",
    "format_confusion_matrix_text",
    "format_metrics_summary",
    "build_model_pipelines",
    "build_production_pipeline",
    "evaluate_held_out_test",
    "evaluate_pipeline_cv",
    "run_tabular_benchmarks",
    "save_experiment_report",
    "serialize_baseline_model",
    "PredictionResult",
    "TabularPredictor",
    "RESEARCH_DISCLAIMER",
]

