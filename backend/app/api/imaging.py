"""Research-only chest X-ray analysis API."""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.app.db.models import AnalysisRun, User
from backend.app.db.session import get_db
from backend.app.schemas.analysis import AnalysisRunResponse
from backend.app.schemas.imaging import ImagingInferenceRequest
from backend.app.security.dependencies import require_permission
from backend.app.security.patient_access import require_patient_access
from backend.app.security.roles import Permission
from backend.app.services.exceptions import (
    ConsistencyError,
    EntityNotFoundError,
)
from backend.app.services.imaging import ImagingMLService
from backend.app.settings import Settings

logger = logging.getLogger("arogya.api.imaging")

router = APIRouter(tags=["Research Analysis & AI Models"])


@router.post(
    "/patients/{patient_id}/analysis/imaging",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze a chest X-ray",
    description=(
        "Runs research-only chest X-ray inference on a previously "
        "uploaded image. Results are not a medical diagnosis."
    ),
)
def execute_imaging_analysis(
    patient_id: UUID,
    payload: ImagingInferenceRequest,
    current_user: User = Depends(
        require_permission(Permission.ANALYSIS_EXECUTE)
    ),
    session: Session = Depends(get_db),
) -> AnalysisRunResponse:
    """Execute and persist a chest X-ray analysis run."""

    require_patient_access(session, current_user, patient_id)
    service = ImagingMLService(session)

    try:
        run = service.execute_patient_imaging_analysis(
            patient_id=patient_id,
            asset_id=payload.asset_id,
            encounter_id=payload.encounter_id,
            generate_heatmap=payload.generate_heatmap,
            heatmap_label=payload.heatmap_label,
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

    except ValueError as exc:
        session.rollback()

        message = str(exc)
        error_status = (
            status.HTTP_404_NOT_FOUND
            if "not found" in message.lower()
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )

        raise HTTPException(
            status_code=error_status,
            detail=message,
        ) from exc

    except Exception as exc:
        session.rollback()

        logger.exception(
            "Unexpected error while creating chest X-ray analysis "
            "for patient %s",
            patient_id,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to process the imaging analysis request.",
        ) from exc


@router.get(
    "/analysis-runs/{run_id}/imaging/heatmap",
    response_class=FileResponse,
    summary="Retrieve an imaging Grad-CAM heatmap",
    description=(
        "Returns the generated research-only Grad-CAM image for a completed "
        "imaging analysis run."
    ),
)
def get_imaging_heatmap(
    run_id: UUID,
    request: Request,
    current_user: User = Depends(
        require_permission(Permission.ANALYSIS_READ)
    ),
    session: Session = Depends(get_db),
) -> FileResponse:
    """Return a run's heatmap without exposing its server-side storage path."""
    run = session.get(AnalysisRun, run_id)

    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imaging analysis run was not found.",
        )
    require_patient_access(session, current_user, run.patient_id)

    if (
        run.model_name != ImagingMLService.MODEL_NAME
        or run.status != "completed"
        or not isinstance(run.results_summary, dict)
        or not isinstance(run.results_summary.get("gradcam"), dict)
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No Grad-CAM heatmap is available for this analysis run.",
        )

    settings: Settings = request.app.state.settings
    storage_root = Path(settings.upload_storage_dir).resolve()
    heatmap_path = storage_root.parent / "imaging_artifacts" / f"{run.id.hex}.png"

    if not heatmap_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The Grad-CAM heatmap artifact is unavailable.",
        )

    return FileResponse(
        path=heatmap_path,
        media_type="image/png",
        headers={"Cache-Control": "private, no-store"},
    )