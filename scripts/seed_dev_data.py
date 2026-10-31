#!/usr/bin/env python3
"""Arogya AI — Synthetic Development Seed Data Generator.

Module 3, Phase 3.5: Alembic Migrations & Synthetic Development Seed Data.
Populates a confirmed local development or testing database with strictly synthetic,
illustrative records across all 8 clinical domain entities and user roles.

SAFETY & GOVERNANCE RULES:
1. Environment Protection: Refuses execution if APP_ENV is 'production', 'prod', or 'staging'.
2. Explicit Opt-in: Requires CLI flag '--confirm-dev-seed' to run.
3. Zero-PHI Guarantee: All generated names, MRNs, and values are fictional synthetic fixtures.
4. Zero Real Credentials: Generates no usable passwords or login privileges; account password
   hashes are set to cryptographically invalid disabled markers.
5. Idempotent Execution: Uses stable, deterministic UUIDs (UUIDv5) to ensure repeated runs
   produce identical state without duplication or primary key conflicts.
6. Transactional Safety: Executes inside a managed transaction; rolls back completely on error.
7. Non-Destructive: Never drops tables or truncates existing user data.
"""

import argparse
from datetime import date, datetime, timezone
import logging
import os
from pathlib import Path
import sys
import uuid

# Ensure repository root is on sys.path
_repo_root = Path(__file__).resolve().parent.parent
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from backend.app.db.session import create_db_engine, get_session_factory
from backend.app.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("arogya.seed")

# Deterministic namespace UUID for stable synthetic record IDs
SEED_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-5000-8000-112233445566")

# Sentinel string indicating a disabled, non-authenticating account
LOCKED_PASSWORD_SENTINEL = "!LOCKED_SYNTHETIC_DEVELOPMENT_ACCOUNT_NO_CREDENTIALS!"


class SeedSafetyError(Exception):
    """Raised when environment or confirmation safety checks fail."""

    pass


def generate_seed_id(entity_name: str, natural_key: str) -> uuid.UUID:
    """Generate a deterministic UUIDv5 identifier for a synthetic entity."""
    return uuid.uuid5(SEED_NAMESPACE, f"{entity_name}:{natural_key}")


def verify_seed_environment(app_env: str | None = None) -> None:
    """Verify that current environment settings permit synthetic seed generation.

    Args:
        app_env: Optional environment name; defaults to application settings.

    Raises:
        SeedSafetyError: If running in production or staging environments.
    """
    current_env = (app_env or get_settings().app_env).strip().lower()
    forbidden_environments = {"production", "prod", "staging", "live"}

    if current_env in forbidden_environments:
        raise SeedSafetyError(
            f"REFUSING TO RUN: Synthetic development seed script cannot run in '{current_env}' environment. "
            "Seed data is strictly restricted to local development and test databases."
        )


def seed_development_data(
    session: Session,
    *,
    app_env: str | None = None,
    confirmed: bool = False,
) -> dict[str, int]:
    """Populate database with synthetic development records inside an active session.

    Args:
        session: Active SQLAlchemy session.
        app_env: Current environment string.
        confirmed: Explicit confirmation flag (must be True).

    Returns:
        Dictionary detailing the count of created records per entity type.

    Raises:
        SeedSafetyError: If safety checks or explicit confirmation fail.
    """
    if not confirmed:
        raise SeedSafetyError(
            "Safety check failed: explicit opt-in confirmation (confirmed=True) "
            "is required to seed development data."
        )

    verify_seed_environment(app_env)

    counts: dict[str, int] = {
        "roles": 0,
        "users": 0,
        "user_roles": 0,
        "patients": 0,
        "encounters": 0,
        "observations": 0,
        "uploaded_assets": 0,
        "analysis_runs": 0,
        "audit_events": 0,
    }

    # -------------------------------------------------------------------------
    # 1. System Roles
    # -------------------------------------------------------------------------
    role_specs = [
        ("administrator", "Synthetic administrator role for development testing"),
        ("clinician", "Synthetic clinician role for development testing"),
        ("researcher", "Synthetic researcher role for development testing"),
    ]
    role_map: dict[str, Role] = {}

    for name, description in role_specs:
        role_id = generate_seed_id("role", name)
        existing_role = session.get(Role, role_id)
        if existing_role is None:
            # Check by unique name in case ID differs
            existing_role = session.scalar(select(Role).where(Role.name == name))

        if existing_role is None:
            role = Role(
                id=role_id,
                name=name,
                description=description,
                created_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            )
            session.add(role)
            role_map[name] = role
            counts["roles"] += 1
        else:
            role_map[name] = existing_role

    # Flush roles to establish references
    session.flush()

    # -------------------------------------------------------------------------
    # 2. Synthetic Development User (Zero Usable Credentials)
    # -------------------------------------------------------------------------
    user_id = generate_seed_id("user", "dev_test_user")
    user = session.get(User, user_id)
    if user is None:
        user = session.scalar(select(User).where(User.username == "dev_test_user"))

    if user is None:
        user = User(
            id=user_id,
            username="dev_test_user",
            email="dev.test.user@synthetic.local",
            full_name="Development Test User (Synthetic)",
            hashed_password=LOCKED_PASSWORD_SENTINEL,
            is_active=True,
            created_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
        session.add(user)
        session.flush()
        counts["users"] += 1

    # Associate clinician role to test user if not already linked
    clinician_role = role_map.get("clinician")
    if clinician_role and clinician_role not in user.roles:
        user.roles.append(clinician_role)
        counts["user_roles"] += 1
        session.flush()

    # -------------------------------------------------------------------------
    # 3. Synthetic Patient (Zero PHI, Pseudonymous MRN)
    # -------------------------------------------------------------------------
    patient_id = generate_seed_id("patient", "SYNTH-PAT-0001")
    patient = session.get(Patient, patient_id)
    if patient is None:
        patient = session.scalar(select(Patient).where(Patient.mrn_pseudonym == "SYNTH-PAT-0001"))

    if patient is None:
        patient = Patient(
            id=patient_id,
            mrn_pseudonym="SYNTH-PAT-0001",
            birth_date=date(1980, 1, 1),
            biological_sex="unknown",
            is_synthetic=True,
            created_at=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 10, 8, 0, tzinfo=timezone.utc),
        )
        session.add(patient)
        session.flush()
        counts["patients"] += 1

    # -------------------------------------------------------------------------
    # 4. Clinical Encounter
    # -------------------------------------------------------------------------
    encounter_id = generate_seed_id("encounter", "SYNTH-ENC-0001")
    encounter = session.get(Encounter, encounter_id)

    if encounter is None:
        encounter = Encounter(
            id=encounter_id,
            patient_id=patient.id,
            encounter_type="synthetic",
            status="completed",
            start_time=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
            created_at=datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 15, 11, 0, tzinfo=timezone.utc),
        )
        session.add(encounter)
        session.flush()
        counts["encounters"] += 1

    # -------------------------------------------------------------------------
    # 5. Clinical Observations (Quantitative & Qualitative Segregation)
    # -------------------------------------------------------------------------
    obs_specs = [
        (
            "obs:hr",
            "8867-4",
            "Heart rate (Synthetic)",
            72.0,
            None,
            "bpm",
            {"synthetic": True, "device": "simulated_cardiac_monitor"},
        ),
        (
            "obs:temp",
            "8310-5",
            "Body temperature (Synthetic)",
            37.0,
            None,
            "Cel",
            {"synthetic": True, "device": "simulated_digital_thermometer"},
        ),
        (
            "obs:cough",
            "49727-2",
            "Cough symptom assessment (Synthetic)",
            None,
            "Mild intermittent dry cough; clear breath sounds (synthetic note)",
            None,
            {"synthetic": True, "assessment_mode": "synthetic_intake"},
        ),
    ]

    for natural_key, code, display_name, num_val, text_val, unit, metadata in obs_specs:
        obs_id = generate_seed_id("observation", natural_key)
        if session.get(Observation, obs_id) is None:
            obs = Observation(
                id=obs_id,
                encounter_id=encounter.id,
                patient_id=patient.id,
                code=code,
                display_name=display_name,
                numeric_value=num_val,
                text_value=text_val,
                unit=unit,
                observed_at=datetime(2026, 1, 15, 10, 15, tzinfo=timezone.utc),
                source_metadata=metadata,
                created_at=datetime(2026, 1, 15, 10, 15, tzinfo=timezone.utc),
            )
            session.add(obs)
            counts["observations"] += 1

    session.flush()

    # -------------------------------------------------------------------------
    # 6. Uploaded Asset Metadata (Placeholder Reference Only)
    # -------------------------------------------------------------------------
    asset_id = generate_seed_id("asset", "SYNTH-ASSET-0001")
    asset = session.get(UploadedAsset, asset_id)
    placeholder_path = "synthetic/assets/placeholders/synthetic_chest_phantom_001.png"

    if asset is None:
        asset = session.scalar(
            select(UploadedAsset).where(UploadedAsset.storage_path == placeholder_path)
        )

    if asset is None:
        asset = UploadedAsset(
            id=asset_id,
            patient_id=patient.id,
            encounter_id=encounter.id,
            original_filename="synthetic_chest_phantom_001.png",
            media_type="image/png",
            file_size_bytes=1048576,
            storage_path=placeholder_path,
            checksum_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            created_at=datetime(2026, 1, 15, 10, 20, tzinfo=timezone.utc),
        )
        session.add(asset)
        session.flush()
        counts["uploaded_assets"] += 1

    # -------------------------------------------------------------------------
    # 7. Analysis Run (Explicitly Labeled Demo Output)
    # -------------------------------------------------------------------------
    run_id = generate_seed_id("analysis_run", "SYNTH-RUN-0001")
    analysis_run = session.get(AnalysisRun, run_id)

    if analysis_run is None:
        analysis_run = AnalysisRun(
            id=run_id,
            patient_id=patient.id,
            encounter_id=encounter.id,
            asset_id=asset.id,
            model_name="synthetic_baseline_screener",
            model_version="v0.1.0-demo",
            status="completed",
            parameters={"mode": "synthetic_demonstration", "threshold": 0.5},
            results_summary={
                "risk_score": 0.12,
                "label": "nominal",
                "disclaimer": "SYNTHETIC DEMO OUTPUT ONLY. NOT CLINICALLY VALIDATED.",
            },
            error_message=None,
            started_at=datetime(2026, 1, 15, 10, 25, tzinfo=timezone.utc),
            completed_at=datetime(2026, 1, 15, 10, 26, tzinfo=timezone.utc),
            created_at=datetime(2026, 1, 15, 10, 25, tzinfo=timezone.utc),
        )
        session.add(analysis_run)
        session.flush()
        counts["analysis_runs"] += 1

    # -------------------------------------------------------------------------
    # 8. Audit Event
    # -------------------------------------------------------------------------
    audit_id = generate_seed_id("audit_event", "SYNTH-AUDIT-0001")
    audit_event = session.get(AuditEvent, audit_id)

    if audit_event is None:
        audit_event = AuditEvent(
            id=audit_id,
            event_type="system.seed_initialization",
            actor_id=user.id,
            action="execute",
            resource_type="system",
            resource_id="synthetic_seed_v1",
            description="Synthetic development seed dataset initialized (Module 3, Phase 3.5)",
            ip_address="127.0.0.1",
            event_metadata={"environment": "development", "synthetic": True},
            created_at=datetime(2026, 1, 15, 10, 30, tzinfo=timezone.utc),
        )
        session.add(audit_event)
        session.flush()
        counts["audit_events"] += 1

    return counts


def run_seed_cli(args: list[str] | None = None) -> int:
    """CLI runner for synthetic development seed data generation."""
    parser = argparse.ArgumentParser(
        description="Arogya AI - Synthetic Development Seed Data Generator"
    )
    parser.add_argument(
        "--confirm-dev-seed",
        action="store_true",
        help="Explicit confirmation to populate synthetic records into local development database",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Optional database connection URL override (defaults to DATABASE_URL in settings)",
    )

    parsed = parser.parse_args(args)

    if not parsed.confirm_dev_seed:
        logger.error(
            "Safety check failed: You must specify --confirm-dev-seed to run this script."
        )
        return 1

    try:
        verify_seed_environment()
    except SeedSafetyError as exc:
        logger.error("%s", exc)
        return 1

    target_url = parsed.database_url or get_settings().database_url
    if not target_url:
        logger.error(
            "DATABASE_URL is not configured in settings or CLI arguments. Cannot connect to database."
        )
        return 1

    try:
        engine = create_db_engine(target_url)
        factory = get_session_factory(engine=engine)

        with factory() as session:
            with session.begin():
                logger.info("Seeding synthetic development data into database...")
                counts = seed_development_data(session, confirmed=True)

        logger.info("Synthetic seed completed successfully. Records created: %s", counts)
        return 0
    except Exception as exc:
        logger.exception("Failed to seed development data: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(run_seed_cli())
