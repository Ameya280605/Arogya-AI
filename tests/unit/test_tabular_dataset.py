"""Arogya AI - Unit Tests for Tabular Dataset Loader & Validator.

Module 9: Tabular ML Baseline Classification.
Tests Exasens CSV parsing, column normalization, schema validation, cohort isolation,
and reproducible stratified splitting.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from ml.tabular.src.dataset import (
    ALL_FEATURES,
    BIOSENSOR_FEATURES,
    CANONICAL_COLUMNS,
    DEFAULT_DATASET_PATH,
    DEMOGRAPHIC_FEATURES,
    DIAGNOSIS_CLASSES,
    EXPECTED_BIOSENSOR_COHORT_COUNT,
    EXPECTED_FULL_COHORT_COUNT,
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


@pytest.mark.unit
def test_csv_file_exists():
    """Verify that the Exasens raw CSV file is present at the expected location."""
    assert DEFAULT_DATASET_PATH.exists(), f"Exasens CSV missing at {DEFAULT_DATASET_PATH}"
    assert DEFAULT_DATASET_PATH.stat().st_size > 0


@pytest.mark.unit
def test_load_exasens_raw_not_found():
    """Verify FileNotFoundError when providing a non-existent path."""
    with pytest.raises(FileNotFoundError):
        load_exasens_raw(Path("non_existent_path.csv"))


@pytest.mark.unit
def test_clean_exasens_data_normalization():
    """Verify multi-row header normalization and column pruning."""
    raw_df = load_exasens_raw()
    clean_df = clean_exasens_data(raw_df)

    # Must contain exactly 399 rows and 9 canonical columns
    assert clean_df.shape == (EXPECTED_FULL_COHORT_COUNT, len(CANONICAL_COLUMNS))
    assert list(clean_df.columns) == CANONICAL_COLUMNS

    # Legend strings and blank columns (indices 9-12) must be completely dropped
    assert "Gender " not in clean_df.columns
    assert "Somking" not in clean_df.columns

    # Verify column types
    assert clean_df["Gender"].dtype in (np.int32, np.int64)
    assert clean_df["Age"].dtype in (np.int32, np.int64)
    assert clean_df["Smoking"].dtype in (np.int32, np.int64)
    for bio_col in BIOSENSOR_FEATURES:
        assert clean_df[bio_col].dtype in (np.float32, np.float64)


@pytest.mark.unit
def test_validation_rules_on_clean_data():
    """Verify that validate_exasens_dataframe passes for the canonical dataset."""
    raw_df = load_exasens_raw()
    clean_df = clean_exasens_data(raw_df)
    summary = validate_exasens_dataframe(clean_df)

    assert summary["total_records"] == EXPECTED_FULL_COHORT_COUNT
    assert summary["complete_biosensor_records"] == EXPECTED_BIOSENSOR_COHORT_COUNT
    assert summary["missing_biosensor_records"] == 299

    # Check exact diagnosis breakdown
    diag = summary["diagnosis_distribution"]
    assert diag["HC"] == 160
    assert diag["Asthma"] == 80
    assert diag["Infected"] == 80
    assert diag["COPD"] == 79


@pytest.mark.unit
def test_validation_fails_on_corrupted_data():
    """Verify that validate_exasens_dataframe catches invalid diagnosis labels."""
    raw_df = load_exasens_raw()
    clean_df = clean_exasens_data(raw_df)

    # Inject unknown diagnosis
    corrupted_df = clean_df.copy()
    corrupted_df.loc[0, TARGET_COLUMN] = "UnknownDisease"
    with pytest.raises(ValueError, match="Unexpected diagnosis classes"):
        validate_exasens_dataframe(corrupted_df)

    # Inject invalid gender
    corrupted_gender_df = clean_df.copy()
    corrupted_gender_df.loc[0, "Gender"] = 5
    with pytest.raises(ValueError, match="Gender contains invalid values"):
        validate_exasens_dataframe(corrupted_gender_df)


@pytest.mark.unit
def test_id_isolation_from_feature_matrices():
    """Critical safety check: Ensure ID column is never leaked into feature matrices."""
    raw_df = load_exasens_raw()
    clean_df = clean_exasens_data(raw_df)

    # Full cohort with demographic features
    X_full_demo, _ = get_full_cohort(clean_df, features="demographic", return_X_y=True)
    assert ID_COLUMN not in X_full_demo.columns
    assert list(X_full_demo.columns) == DEMOGRAPHIC_FEATURES

    # Full cohort with all features
    X_full_all, _ = get_full_cohort(clean_df, features="all", return_X_y=True)
    assert ID_COLUMN not in X_full_all.columns
    assert set(X_full_all.columns) == set(ALL_FEATURES)

    # Complete biosensor cohort
    X_bio, _ = get_complete_biosensor_cohort(clean_df, return_X_y=True)
    assert ID_COLUMN not in X_bio.columns
    assert set(X_bio.columns) == set(ALL_FEATURES)


@pytest.mark.unit
def test_full_cohort_size_and_missingness():
    """Verify full cohort properties: 399 patients, zero missing in demographics."""
    raw_df = load_exasens_raw()
    clean_df = clean_exasens_data(raw_df)

    X, y = get_full_cohort(clean_df, features="demographic", return_X_y=True)
    assert len(X) == EXPECTED_FULL_COHORT_COUNT
    assert len(y) == EXPECTED_FULL_COHORT_COUNT

    # Demographics must have 0 missing values
    assert X[DEMOGRAPHIC_FEATURES].isnull().sum().sum() == 0
    assert y.isnull().sum() == 0

    # Target class distribution check
    assert y.value_counts().to_dict() == {
        "HC": 160,
        "Asthma": 80,
        "Infected": 80,
        "COPD": 79,
    }


@pytest.mark.unit
def test_complete_biosensor_cohort_size_and_completeness():
    """Verify complete biosensor cohort: exactly 100 cases with no missing measurements."""
    raw_df = load_exasens_raw()
    clean_df = clean_exasens_data(raw_df)

    X_bio, y_bio = get_complete_biosensor_cohort(clean_df, return_X_y=True)
    assert len(X_bio) == EXPECTED_BIOSENSOR_COHORT_COUNT
    assert len(y_bio) == EXPECTED_BIOSENSOR_COHORT_COUNT

    # All 7 features must be present with zero missing values
    assert set(X_bio.columns) == set(ALL_FEATURES)
    assert X_bio.isnull().sum().sum() == 0
    assert y_bio.isnull().sum() == 0

    # Target distribution for complete biosensor cohort
    assert y_bio.value_counts().to_dict() == {
        "COPD": 40,
        "HC": 40,
        "Asthma": 10,
        "Infected": 10,
    }


@pytest.mark.unit
def test_reproducible_stratified_split_full_cohort():
    """Verify reproducible stratified splitting on full cohort preserves proportions."""
    dataset = ExasensDataset.load()
    X_train, X_test, y_train, y_test = dataset.split_full_cohort(
        features="demographic",
        test_size=0.2,
        random_state=42,
    )

    # 399 total -> 80% train = 319, 20% test = 80
    assert len(X_train) == 319
    assert len(X_test) == 80
    assert len(y_train) == 319
    assert len(y_test) == 80

    # Ensure train and test index sets are disjoint (zero data leakage)
    assert set(X_train.index).isdisjoint(set(X_test.index))

    # Proportions must match the full cohort distribution (~40% HC, ~20% others)
    test_proportions = y_test.value_counts(normalize=True).to_dict()
    assert pytest.approx(test_proportions["HC"], abs=0.02) == 0.40
    assert pytest.approx(test_proportions["Asthma"], abs=0.02) == 0.20
    assert pytest.approx(test_proportions["Infected"], abs=0.02) == 0.20
    assert pytest.approx(test_proportions["COPD"], abs=0.02) == 0.20

    # Reproducibility check: identical seed yields identical splits
    X_tr2, X_te2, _, _ = dataset.split_full_cohort(features="demographic", test_size=0.2, random_state=42)
    pd.testing.assert_frame_equal(X_train, X_tr2)
    pd.testing.assert_frame_equal(X_test, X_te2)


@pytest.mark.unit
def test_reproducible_stratified_split_biosensor_cohort():
    """Verify reproducible stratified splitting on biosensor cohort preserves proportions."""
    dataset = ExasensDataset.load()
    X_train, X_test, y_train, y_test = dataset.split_biosensor_cohort(
        test_size=0.2,
        random_state=42,
    )

    # 100 total -> 80% train = 80, 20% test = 20
    assert len(X_train) == 80
    assert len(X_test) == 20
    assert len(y_train) == 80
    assert len(y_test) == 20

    # Disjoint indices
    assert set(X_train.index).isdisjoint(set(X_test.index))

    # Exact stratified counts in test split: 8 HC, 8 COPD, 2 Asthma, 2 Infected
    test_counts = y_test.value_counts().to_dict()
    assert test_counts == {"HC": 8, "COPD": 8, "Asthma": 2, "Infected": 2}

    # Features check
    assert list(X_train.columns) == ALL_FEATURES

