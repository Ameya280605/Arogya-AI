"""Arogya AI — Tabular Machine Learning Service.

Module 9: Tabular ML Baseline Classification & Biosensor Risk Modeling.
Connects the standalone TabularPredictor inference pipeline to the backend platform,
persisting execution lifecycle, parameters, outputs, and errors strictly within the
segregated AnalysisRun data model.

SAFETY & GOVERNANCE NOTICE:
Inference results represent experimental research signals and are strictly segregated
from validated clinical observations. Outputs must NEVER be treated as certified diagnoses.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.db.models import AnalysisRun
from backend.app.schemas.analysis import AnalysisRunCreate, TabularInferenceRequest
from backend.app.services.clinical import ClinicalService
from backend.app.services.exceptions import ConsistencyError, EntityNotFoundError
from ml.tabular.src.predictor import TabularPredictor

logger = logging.getLogger(__name__)

# Singleton predictor instance protected by thread lock
_predictor_instance: TabularPredictor | None = None
_predictor_lock = threading.Lock()


def get_tabular_predictor() -> TabularPredictor:
    """Retrieve or lazily initialize the singleton TabularPredictor instance.

    Thread-safe and verifies the model's SHA-256 cryptographic checksum upon loading.
    """
    global _predictor_instance
    if _predictor_instance is None:
        with _predictor_lock:
            if _predictor_instance is None:
                logger.info("Initializing singleton TabularPredictor with SHA-256 integrity check...")
                _predictor_instance = TabularPredictor()
    return _predictor_instance


class TabularMLService:
    """Domain service managing the lifecycle and execution of tabular ML analysis runs."""

    def __init__(
        self,
        session: Session,
        predictor: TabularPredictor | None = None,
    ) -> None:
        """Initialize the TabularMLService with database session and predictor.

        Args:
            session: Active SQLAlchemy database session.
            predictor: Optional TabularPredictor override (useful for testing).
        """
        self.session = session
        self.clinical_service = ClinicalService(session)
        self.predictor = predictor or get_tabular_predictor()

    def execute_patient_tabular_analysis(
        self,
        patient_id: UUID,
        request_data: TabularInferenceRequest,
        actor_id: UUID | None = None,
    ) -> AnalysisRun:
        """Execute tabular inference for a patient and record full lifecycle in AnalysisRun.

        Lifecycle:
        1. Validates patient existence and encounter referential integrity.
        2. Creates an AnalysisRun record in 'queued' state with input parameters.
        3. Advances lifecycle to 'running' with started_at timestamp.
        4. Invokes TabularPredictor.predict_single().
        5. On success: Updates AnalysisRun to 'completed' with structured results_summary.
        6. On failure: Updates AnalysisRun to 'failed' with error_message.

        Args:
            patient_id: Target patient UUID.
            request_data: Validated clinical and biosensor feature payload.
            actor_id: Optional UUID of the authenticated practitioner requesting analysis.

        Returns:
            Persisted AnalysisRun database model containing execution history and results.

        Raises:
            EntityNotFoundError: If the patient or encounter does not exist.
            ConsistencyError: If the encounter does not belong to the specified patient.
        """
        # 1. Initiate run via ClinicalService (enforcing referential integrity and audit trail)
        run_create = AnalysisRunCreate(
            patient_id=patient_id,
            encounter_id=request_data.encounter_id,
            asset_id=None,
            model_name=self.predictor.model_name,
            model_version=self.predictor.model_version,
            parameters=request_data.parameters,
        )
        run = self.clinical_service.create_analysis_run(data=run_create, actor_id=actor_id)

        # 2. Mark execution commencement
        started_at = datetime.now(timezone.utc)
        run = self.clinical_service.update_analysis_status(
            run_id=run.id,
            status="running",
            started_at=started_at,
            actor_id=actor_id,
        )

        # 3. Format input dictionary for TabularPredictor
        feature_dict: dict[str, Any] = {
            "Age": request_data.age,
            "Gender": request_data.gender,
            "Smoking": request_data.smoking,
            "Imaginary_Min": request_data.imaginary_min,
            "Imaginary_Avg": request_data.imaginary_avg,
            "Real_Min": request_data.real_min,
            "Real_Avg": request_data.real_avg,
        }

        # 4. Execute prediction with failure isolation
        try:
            prediction_result = self.predictor.predict_single(feature_dict)
            completed_at = datetime.now(timezone.utc)

            # Segregate model outputs strictly into results_summary
            results_payload = prediction_result.to_dict()

            updated_run = self.clinical_service.update_analysis_status(
                run_id=run.id,
                status="completed",
                results_summary=results_payload,
                started_at=started_at,
                completed_at=completed_at,
                actor_id=actor_id,
            )
            return updated_run

        except Exception as exc:
            logger.error(f"Tabular inference failed for AnalysisRun '{run.id}': {exc}", exc_info=True)
            completed_at = datetime.now(timezone.utc)
            failed_run = self.clinical_service.update_analysis_status(
                run_id=run.id,
                status="failed",
                error_message=f"Inference execution error: {exc}",
                started_at=started_at,
                completed_at=completed_at,
                actor_id=actor_id,
            )
            return failed_run

