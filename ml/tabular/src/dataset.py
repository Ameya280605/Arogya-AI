"""Arogya AI - Exasens Tabular Dataset Loader, Validator & Splitter.

Module 9: Tabular ML Baseline Classification.
Parses, cleans, validates, and partitions the Exasens respiratory biomarker dataset.

SAFETY & GOVERNANCE NOTICE:
This module supports research prototyping and baseline ML model evaluation only.
It is NOT a validated diagnostic medical device or certified clinical system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

logger = logging.getLogger(__name__)

# Canonical project paths
MODULE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET_PATH = MODULE_ROOT / "data" / "exasens.csv"

# Target & Feature definitions
TARGET_COLUMN: str = "Diagnosis"
ID_COLUMN: str = "ID"

DIAGNOSIS_CLASSES: tuple[str, ...] = ("HC", "Asthma", "Infected", "COPD")

DEMOGRAPHIC_FEATURES: list[str] = ["Age", "Gender", "Smoking"]
BIOSENSOR_FEATURES: list[str] = [
    "Imaginary_Min",
    "Imaginary_Avg",
    "Real_Min",
    "Real_Avg",
]
ALL_FEATURES: list[str] = DEMOGRAPHIC_FEATURES + BIOSENSOR_FEATURES

# Expected canonical columns in normalized cleaned dataframe
CANONICAL_COLUMNS: list[str] = [
    TARGET_COLUMN,
    ID_COLUMN,
    "Imaginary_Min",
    "Imaginary_Avg",
    "Real_Min",
    "Real_Avg",
    "Gender",
    "Age",
    "Smoking",
]

# Expected dataset sizes
EXPECTED_FULL_COHORT_COUNT: int = 399
EXPECTED_BIOSENSOR_COHORT_COUNT: int = 100


def load_exasens_raw(file_path: Path | str | None = None) -> pd.DataFrame:
    """Load raw Exasens CSV file without header inference.

    Args:
        file_path: Optional path to exasens.csv. Defaults to DEFAULT_DATASET_PATH.

    Returns:
        Raw unparsed DataFrame including composite Excel headers and blank rows.

    Raises:
        FileNotFoundError: If the specified CSV file does not exist.
        ValueError: If file is empty or corrupted.
    """
    path = Path(file_path) if file_path is not None else DEFAULT_DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"Exasens dataset file was not found at '{path}'")

    raw_df = pd.read_csv(path, header=None, low_memory=False)
    if raw_df.empty or len(raw_df) < 4:
        raise ValueError(f"Exasens dataset at '{path}' is empty or contains insufficient rows.")

    return raw_df


def clean_exasens_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize multi-row headers, prune legend/blank columns, and cast data types.

    The original Exasens export contains:
    - Row 0: General variable names and sensor group labels
    - Row 1: Blank separator
    - Row 2: Sub-headers ('Min', 'Avg.') and column notes
    - Rows 3+: 399 individual patient records
    - Columns 9-10: Blank padding
    - Columns 11-12: Legend strings (e.g. 'Male=1', 'Non-smoker=1')

    Args:
        raw_df: Raw DataFrame loaded via `load_exasens_raw`.

    Returns:
        Cleaned, normalized DataFrame containing exactly 399 rows and 9 canonical columns.
    """
    # Extract data rows starting from row 3 (0-indexed) and first 9 relevant columns
    df = raw_df.iloc[3:, :9].copy()
    df.columns = CANONICAL_COLUMNS
    df = df.reset_index(drop=True)

    # Clean string identifiers and target
    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(str).str.strip()
    df[ID_COLUMN] = df[ID_COLUMN].astype(str).str.strip()

    # Convert demographic variables to strict integer types
    for col in ["Gender", "Age", "Smoking"]:
        df[col] = pd.to_numeric(df[col], errors="raise").astype(int)

    # Convert dielectric biosensor measurements to numeric float (preserving NaNs)
    for col in BIOSENSOR_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    return df


def validate_exasens_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Validate data integrity, schema consistency, and clinical constraints.

    Checks:
    - Presence of all canonical columns.
    - Expected row counts for full cohort (399) and complete biosensor cohort (100).
    - Valid diagnosis categories (HC, Asthma, Infected, COPD).
    - Valid demographic ranges (Gender in {0, 1}, Age in [1, 120], Smoking in {1, 2, 3}).
    - Zero missing values in demographics, ID, and target.
    - Exactly 299 missing values in biosensor features across full cohort.
    - Confirms ID is tracked separately and excluded from feature sets.

    Args:
        df: Cleaned DataFrame produced by `clean_exasens_data`.

    Returns:
        Dictionary summarizing validation statistics.

    Raises:
        ValueError: If any invariant or integrity constraint is violated.
    """
    # 1. Column presence check
    missing_cols = set(CANONICAL_COLUMNS) - set(df.columns)
    if missing_cols:
        raise ValueError(f"Cleaned dataset missing expected canonical columns: {missing_cols}")

    # 2. Total record count check
    total_records = len(df)
    if total_records != EXPECTED_FULL_COHORT_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_FULL_COHORT_COUNT} patient records, but found {total_records}."
        )

    # 3. Target label validation
    unique_diagnoses = set(df[TARGET_COLUMN].unique())
    expected_diagnoses = set(DIAGNOSIS_CLASSES)
    if not unique_diagnoses.issubset(expected_diagnoses):
        invalid_labels = unique_diagnoses - expected_diagnoses
        raise ValueError(f"Unexpected diagnosis classes encountered: {invalid_labels}")

    diagnosis_counts = df[TARGET_COLUMN].value_counts().to_dict()

    # 4. Mandatory demographic non-null check
    for col in [ID_COLUMN, TARGET_COLUMN] + DEMOGRAPHIC_FEATURES:
        null_count = df[col].isnull().sum()
        if null_count > 0:
            raise ValueError(f"Column '{col}' must not contain missing values (found {null_count}).")

    # 5. Demographic value domain validation
    invalid_gender = set(df["Gender"].unique()) - {0, 1}
    if invalid_gender:
        raise ValueError(f"Gender contains invalid values: {invalid_gender} (expected {0, 1})")

    invalid_smoking = set(df["Smoking"].unique()) - {1, 2, 3}
    if invalid_smoking:
        raise ValueError(f"Smoking contains invalid values: {invalid_smoking} (expected {1, 2, 3})")

    if (df["Age"] < 1).any() or (df["Age"] > 120).any():
        raise ValueError(f"Age values outside physiological bounds [1, 120]: min={df['Age'].min()}, max={df['Age'].max()}")

    # 6. Biosensor missingness check
    biosensor_mask = df[BIOSENSOR_FEATURES].notnull().all(axis=1)
    complete_biosensor_count = int(biosensor_mask.sum())
    if complete_biosensor_count != EXPECTED_BIOSENSOR_COHORT_COUNT:
        raise ValueError(
            f"Expected exactly {EXPECTED_BIOSENSOR_COHORT_COUNT} complete biosensor records, "
            f"found {complete_biosensor_count}."
        )

    missing_sensor_records = total_records - complete_biosensor_count
    for col in BIOSENSOR_FEATURES:
        missing_count = int(df[col].isnull().sum())
        if missing_count != missing_sensor_records:
            raise ValueError(
                f"Column '{col}' has {missing_count} missing entries (expected {missing_sensor_records})."
            )

    return {
        "total_records": total_records,
        "complete_biosensor_records": complete_biosensor_count,
        "missing_biosensor_records": missing_sensor_records,
        "diagnosis_distribution": diagnosis_counts,
        "demographic_ranges": {
            "age_min": int(df["Age"].min()),
            "age_max": int(df["Age"].max()),
            "male_count": int((df["Gender"] == 1).sum()),
            "female_count": int((df["Gender"] == 0).sum()),
            "smoking_counts": df["Smoking"].value_counts().to_dict(),
        },
    }


def get_full_cohort(
    df: pd.DataFrame,
    features: Literal["demographic", "all"] = "demographic",
    return_X_y: bool = True,
) -> tuple[pd.DataFrame, pd.Series] | pd.DataFrame:
    """Extract the full patient cohort (399 records).

    Strictly excludes the patient `ID` column from features to prevent label leakage.

    Args:
        df: Cleaned Exasens DataFrame.
        features: 'demographic' for [Age, Gender, Smoking] (3 features, 0 missing).
                  'all' for demographic + biosensors (7 features, NaNs preserved for imputation).
        return_X_y: If True, returns (X, y) tuple. If False, returns combined DataFrame.

    Returns:
        (X, y) tuple or DataFrame containing the full cohort without `ID`.
    """
    if features == "demographic":
        feature_cols = DEMOGRAPHIC_FEATURES.copy()
    elif features == "all":
        feature_cols = ALL_FEATURES.copy()
    else:
        raise ValueError(f"Unsupported feature subset '{features}'. Choose 'demographic' or 'all'.")

    if return_X_y:
        X = df[feature_cols].copy()
        y = df[TARGET_COLUMN].copy()
        return X, y

    return df[[TARGET_COLUMN] + feature_cols].copy()


def get_complete_biosensor_cohort(
    df: pd.DataFrame,
    return_X_y: bool = True,
) -> tuple[pd.DataFrame, pd.Series] | pd.DataFrame:
    """Extract the complete biosensor cohort (100 records).

    Includes all records where all 4 saliva dielectric measurements
    (Imaginary_Min, Imaginary_Avg, Real_Min, Real_Avg) are non-null.
    Strictly excludes the patient `ID` column from model features.

    Args:
        df: Cleaned Exasens DataFrame.
        return_X_y: If True, returns (X, y) tuple. If False, returns combined DataFrame.

    Returns:
        (X, y) tuple or DataFrame containing complete cases with all 7 features.
    """
    complete_mask = df[BIOSENSOR_FEATURES].notnull().all(axis=1)
    complete_df = df[complete_mask].copy().reset_index(drop=True)

    feature_cols = ALL_FEATURES.copy()

    if return_X_y:
        X = complete_df[feature_cols].copy()
        y = complete_df[TARGET_COLUMN].copy()
        return X, y

    return complete_df[[TARGET_COLUMN] + feature_cols].copy()


def split_cohort(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Perform reproducible, stratified train/test split.

    DATA LEAKAGE PREVENTION:
    This function splits raw feature representations without fitting scalers,
    imputers, or encoders. Preprocessing must be fit exclusively on X_train.

    Args:
        X: Feature matrix DataFrame.
        y: Target label Series.
        test_size: Proportion of dataset allocated to test split (default: 0.2).
        random_state: Fixed pseudo-random seed for reproducibility (default: 42).
        stratify: Whether to preserve label proportions across splits (default: True).

    Returns:
        Tuple of (X_train, X_test, y_train, y_test).
    """
    stratify_target = y if stratify else None
    return train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_target,
    )


@dataclass(frozen=True)
class ExasensDataset:
    """Immutable container encapsulating cleaned Exasens data and cohort extractors."""

    clean_df: pd.DataFrame
    validation_summary: dict[str, Any]

    @classmethod
    def load(cls, file_path: Path | str | None = None) -> ExasensDataset:
        """Load, clean, validate, and package the Exasens dataset."""
        raw_df = load_exasens_raw(file_path=file_path)
        clean_df = clean_exasens_data(raw_df=raw_df)
        summary = validate_exasens_dataframe(clean_df)
        return cls(clean_df=clean_df, validation_summary=summary)

    def full_cohort(
        self,
        features: Literal["demographic", "all"] = "demographic",
    ) -> tuple[pd.DataFrame, pd.Series]:
        """Return (X, y) for the 399-patient full cohort."""
        return get_full_cohort(self.clean_df, features=features, return_X_y=True)

    def biosensor_cohort(self) -> tuple[pd.DataFrame, pd.Series]:
        """Return (X, y) for the 100-patient complete biosensor cohort."""
        return get_complete_biosensor_cohort(self.clean_df, return_X_y=True)

    def split_full_cohort(
        self,
        features: Literal["demographic", "all"] = "demographic",
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Return stratified (X_train, X_test, y_train, y_test) for the full cohort."""
        X, y = self.full_cohort(features=features)
        return split_cohort(X, y, test_size=test_size, random_state=random_state)

    def split_biosensor_cohort(
        self,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Return stratified (X_train, X_test, y_train, y_test) for the biosensor cohort."""
        X, y = self.biosensor_cohort()
        return split_cohort(X, y, test_size=test_size, random_state=random_state)
