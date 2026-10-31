"""Arogya AI — Synthetic Development Seed Data Tests.

Module 3, Phase 3.5: Alembic Migrations & Synthetic Development Seed Data.
Verifies safety guards (production refusal, explicit opt-in), deterministic
idempotency, transaction rollback on failure, and zero-PHI/zero-credential governance.
"""

from datetime import date, timezone
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.models import (
    AnalysisRun,
    AuditEvent,
    Encounter,
    Observation,
    Patient,
    Role,
    UploadedAsset,
    User,
    user_roles,
)
from scripts.seed_dev_data import (
    LOCKED_PASSWORD_SENTINEL,
    SeedSafetyError,
    generate_seed_id,
    run_seed_cli,
    seed_development_data,
    verify_seed_environment,
)


@pytest.fixture
def sqlite_session() -> Session:
    """Fixture providing an isolated in-memory SQLite session with schema pre-created."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_seed_refuses_production_and_staging_environments() -> None:
    """Verify that environment safety check blocks production, staging, and live execution."""
    for forbidden_env in ["production", "PROD", "Staging", "live", " production "]:
        with pytest.raises(SeedSafetyError) as exc_info:
            verify_seed_environment(app_env=forbidden_env)
        assert "REFUSING TO RUN" in str(exc_info.value)
        assert "environment" in str(exc_info.value)

    # Valid development environments must pass without raising
    verify_seed_environment(app_env="development")
    verify_seed_environment(app_env="test")
    verify_seed_environment(app_env="local")


def test_seed_requires_explicit_confirmation(sqlite_session: Session) -> None:
    """Verify that seed_development_data requires confirmed=True."""
    with pytest.raises(SeedSafetyError) as exc_info:
        seed_development_data(sqlite_session, confirmed=False)
    assert "explicit opt-in confirmation" in str(exc_info.value)


def test_seed_cli_requires_confirmation_flag() -> None:
    """Verify that CLI execution without --confirm-dev-seed exits with code 1."""
    exit_code = run_seed_cli([])
    assert exit_code == 1


def test_seed_generation_creates_all_expected_records(sqlite_session: Session) -> None:
    """Verify that initial seed execution creates all required synthetic records."""
    counts = seed_development_data(sqlite_session, confirmed=True)

    assert counts["roles"] == 3
    assert counts["users"] == 1
    assert counts["user_roles"] == 1
    assert counts["patients"] == 1
    assert counts["encounters"] == 1
    assert counts["observations"] == 3
    assert counts["uploaded_assets"] == 1
    assert counts["analysis_runs"] == 1
    assert counts["audit_events"] == 1

    # Verify counts in database
    assert sqlite_session.scalar(select(func.count(Role.id))) == 3
    assert sqlite_session.scalar(select(func.count(User.id))) == 1
    assert sqlite_session.scalar(select(func.count(Patient.id))) == 1
    assert sqlite_session.scalar(select(func.count(Encounter.id))) == 1
    assert sqlite_session.scalar(select(func.count(Observation.id))) == 3
    assert sqlite_session.scalar(select(func.count(UploadedAsset.id))) == 1
    assert sqlite_session.scalar(select(func.count(AnalysisRun.id))) == 1
    assert sqlite_session.scalar(select(func.count(AuditEvent.id))) == 1


def test_seed_generation_is_strictly_idempotent(sqlite_session: Session) -> None:
    """Verify that repeated seed execution does not create duplicate records."""
    # First execution
    first_counts = seed_development_data(sqlite_session, confirmed=True)
    sqlite_session.commit()

    initial_patient_count = sqlite_session.scalar(select(func.count(Patient.id)))
    initial_user_count = sqlite_session.scalar(select(func.count(User.id)))
    initial_obs_count = sqlite_session.scalar(select(func.count(Observation.id)))

    # Second execution on same database
    second_counts = seed_development_data(sqlite_session, confirmed=True)
    sqlite_session.commit()

    # Second run should create zero new records
    for entity, count in second_counts.items():
        assert count == 0, f"Expected 0 new records for {entity}, got {count}"

    # Database totals must remain identical
    assert sqlite_session.scalar(select(func.count(Patient.id))) == initial_patient_count
    assert sqlite_session.scalar(select(func.count(User.id))) == initial_user_count
    assert sqlite_session.scalar(select(func.count(Observation.id))) == initial_obs_count


def test_seed_transaction_rolls_back_on_error(sqlite_session: Session) -> None:
    """Verify that failures during seed execution trigger complete rollback."""
    # Seed initially
    seed_development_data(sqlite_session, confirmed=True)
    sqlite_session.commit()

    # Attempt a malformed insert that will fail (violating non-nullable constraints)
    with pytest.raises(Exception):
        with sqlite_session.begin():
            sqlite_session.add(Role(id=None, name=None))  # type: ignore[arg-type]
            sqlite_session.flush()

    # Session remains operable after rollback
    assert sqlite_session.scalar(select(func.count(Role.id))) == 3


def test_seed_data_governance_no_phi_and_no_usable_credentials(sqlite_session: Session) -> None:
    """Verify that seeded data strictly conforms to zero-PHI and zero-usable-credentials policies."""
    seed_development_data(sqlite_session, confirmed=True)
    sqlite_session.commit()

    # 1. User Account Governance: password must be locked sentinel, no plaintext password
    user = sqlite_session.scalar(select(User).where(User.username == "dev_test_user"))
    assert user is not None
    assert user.hashed_password == LOCKED_PASSWORD_SENTINEL
    assert "password" not in user.hashed_password.lower() or "no_credentials" in user.hashed_password.lower()
    assert "@synthetic.local" in user.email

    # 2. Patient Governance: must be synthetic with pseudonymous MRN
    patient = sqlite_session.scalar(select(Patient).where(Patient.mrn_pseudonym == "SYNTH-PAT-0001"))
    assert patient is not None
    assert patient.is_synthetic is True
    assert patient.mrn_pseudonym.startswith("SYNTH-")

    # 3. Analysis Run Governance: output must contain clear disclaimer
    run = sqlite_session.scalar(select(AnalysisRun).where(AnalysisRun.model_name == "synthetic_baseline_screener"))
    assert run is not None
    assert run.results_summary is not None
    assert "NOT CLINICALLY VALIDATED" in run.results_summary.get("disclaimer", "")

    # 4. Uploaded Asset Governance: placeholder locator only, not real content
    asset = sqlite_session.scalar(select(UploadedAsset).where(UploadedAsset.original_filename == "synthetic_chest_phantom_001.png"))
    assert asset is not None
    assert asset.storage_path.startswith("synthetic/assets/placeholders/")
