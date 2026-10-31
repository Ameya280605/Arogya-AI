"""Arogya AI — Research Analysis & AI Inference API Endpoints.

Module 9: Tabular ML Baseline Classification & Biosensor Risk Modeling.
Exposes endpoints for submitting and inspecting multimodal research AI runs.
Preserves strict data segregation between AI evaluations and verified clinical observations.

SAFETY & GOVERNANCE NOTICE:
Endpoints serve exploratory research decision-support only.
Model outputs are NOT certified diagnostic conclusions.
"""

import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.errors import ErrorResponse
from backend.app.schemas.analysis import AnalysisRunResponse, TabularInferenceRequest
from backend.app.security.dependencies import require_permission
from backend.app.security.roles import Permission
from backend.app.services.exceptions import ConsistencyError, EntityNotFoundError
from backend.app.services.tabular_ml import TabularMLService, get_tabular_predictor

logger = logging.getLogger("arogya.api.analysis")

router = APIRouter(tags=["Research Analysis & AI Models"])


@router.post(
    "/patients/{patient_id}/analysis/tabular",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Tabular Respiratory Risk Analysis",
    description=(
        "Executes baseline multi-class classification on patient demographics and saliva "
        "dielectric permittivity measurements. Records execution lifecycle, parameters, "
        "and predictions strictly within an AnalysisRun container segregated from primary observations."
    ),
    responses={
        201: {"description": "Tabular analysis run successfully executed and persisted."},
        401: {"description": "Authentication credentials missing or invalid.", "model": ErrorResponse},
        403: {"description": "Insufficient permissions to execute analysis.", "model": ErrorResponse},
        404: {"description": "Referenced patient or encounter not found.", "model": ErrorResponse},
        422: {"description": "Referential consistency or validation violation.", "model": ErrorResponse},
    },
)
def execute_tabular_analysis(
    patient_id: UUID,
    payload: TabularInferenceRequest,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ANALYSIS_READ)),
    session: Session = Depends(get_db),
) -> AnalysisRunResponse:
    """Execute research tabular classification for a patient record."""
    service = TabularMLService(session)

    try:
        run = service.execute_patient_tabular_analysis(
            patient_id=patient_id,
            request_data=payload,
            actor_id=current_user.id,
        )
        session.commit()
        return AnalysisRunResponse.model_validate(run)

    except EntityNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ConsistencyError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        session.rollback()
        logger.error(f"Unexpected error executing tabular analysis for patient '{patient_id}': {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the tabular analysis.",
        ) from exc


@router.get(
    "/analysis/models/tabular",
    response_model=dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Tabular Model Metadata & Disclaimers",
    description="Retrieve model card details, features, version, and non-diagnostic disclaimers.",
    responses={
        200: {"description": "Model metadata retrieved successfully."},
        401: {"description": "Authentication credentials missing or invalid.", "model": ErrorResponse},
    },
)
def get_tabular_model_info(
    current_user: User = Depends(require_permission(Permission.ANALYSIS_READ)),
) -> dict[str, Any]:
    """Retrieve metadata, features, and research disclaimers for the active tabular model."""
    predictor = get_tabular_predictor()
    return predictor.metadata

