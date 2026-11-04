"""Case-centered clinical workspace APIs using existing clinical and ML services."""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.models import AnalysisRun, Encounter, Observation, UploadedAsset, User
from backend.app.db.session import get_db
from backend.app.schemas.analysis import AnalysisRunCreate, AnalysisRunResponse, TabularInferenceRequest
from backend.app.schemas.clinical_workspace import (
    CaseMeasurement,
    ClinicalCaseAnalysisRequest,
    ClinicalCaseCreate,
    ClinicalCaseQuality,
    ClinicalCaseResponse,
    ClinicalCaseUpdate,
)
from backend.app.schemas.encounter import EncounterCreate
from backend.app.schemas.observation import ObservationCreate
from backend.app.security.dependencies import require_permission
from backend.app.security.patient_access import require_patient_access
from backend.app.security.roles import Permission
from backend.app.services.audit import AuditService
from backend.app.services.clinical import ClinicalService
from backend.app.services.exceptions import EntityNotFoundError
from backend.app.services.imaging import ImagingMLService
from backend.app.services.tabular_ml import TabularMLService

logger = logging.getLogger("arogya.api.clinical_workspace")
router = APIRouter(tags=["Clinical Workspace"])

TABULAR_MODEL_NAME = "tabular_exasens_baseline"
TABULAR_MODEL_VERSION = "pending"


def _quality(
    encounter: Encounter,
    observations: list[Observation],
    *,
    for_analysis: bool = False,
) -> ClinicalCaseQuality:
    errors: list[str] = []
    warnings: list[str] = []

    if not (encounter.symptoms or "").strip():
        (errors if for_analysis else warnings).append(
            "Symptoms are not recorded." if for_analysis else "Symptoms are missing."
        )
    if encounter.symptoms and not (encounter.symptom_duration or "").strip():
        warnings.append("Symptom duration is not recorded.")
    if not observations:
        warnings.append("No vital signs or laboratory measurements have been recorded.")

    systolic: float | None = None
    diastolic: float | None = None
    for observation in observations:
        value = observation.numeric_value
        if value is None:
            continue
        name = f"{observation.code} {observation.display_name}".lower()
        unit = (observation.unit or "").strip().lower()
        source = observation.source_metadata or {}
        kind = source.get("kind", "vital")

        if "temperature" in name or "temp" in name or observation.code == "8310-5":
            if unit in {"c", "°c", "degc"}:
                valid = 20 <= value <= 50
            elif unit in {"f", "°f", "degf"}:
                valid = 68 <= value <= 122
            else:
                valid = False
            if not valid:
                errors.append(f"{observation.display_name}: use °C or °F and a plausible numeric value.")
        elif "systolic" in name or observation.code == "8480-6":
            systolic = value
            if not 20 <= value <= 300 or unit not in {"mmhg", "mm hg"}:
                errors.append(f"{observation.display_name}: expected a plausible value in mmHg.")
        elif "diastolic" in name or observation.code == "8462-4":
            diastolic = value
            if not 10 <= value <= 200 or unit not in {"mmhg", "mm hg"}:
                errors.append(f"{observation.display_name}: expected a plausible value in mmHg.")
        elif "heart rate" in name or "pulse" in name or observation.code == "8867-4":
            if not 1 <= value <= 300 or unit not in {"bpm", "beats/min"}:
                errors.append(f"{observation.display_name}: expected a plausible value in bpm.")
        elif "respiratory" in name or observation.code == "9279-1":
            if not 1 <= value <= 100 or unit not in {"breaths/min", "breaths/minute", "/min"}:
                errors.append(f"{observation.display_name}: expected a plausible breaths/min value.")
        elif "spo2" in name or "oxygen saturation" in name or observation.code == "2708-6":
            if not 0 <= value <= 100 or unit not in {"%", "percent"}:
                errors.append(f"{observation.display_name}: expected a value from 0 to 100 percent.")
        elif "height" in name:
            if value <= 0 or unit not in {"cm", "m", "in", "inch", "inches"}:
                errors.append(f"{observation.display_name}: expected a positive value in cm, m, or inches.")
        elif "weight" in name:
            if value <= 0 or unit not in {"kg", "lb", "lbs"}:
                errors.append(f"{observation.display_name}: expected a positive value in kg or lb.")

        if kind == "laboratory":
            low = source.get("reference_low")
            high = source.get("reference_high")
            if low is None and high is None:
                warnings.append(
                    f"{observation.display_name} has no supplied reference range."
                )
            if low is not None and value < low or high is not None and value > high:
                warnings.append(
                    f"{observation.display_name} is outside the supplied reference range; verify the value and range."
                )

    if systolic is not None and diastolic is not None and systolic <= diastolic:
        errors.append("Systolic blood pressure must be greater than diastolic pressure.")

    return ClinicalCaseQuality(
        blocking_errors=errors,
        warnings=warnings,
        ready_for_analysis=not errors,
    )


def _case_response(session: Session, encounter: Encounter) -> ClinicalCaseResponse:
    observations = list(
        session.scalars(
            select(Observation)
            .where(Observation.encounter_id == encounter.id)
            .order_by(Observation.observed_at.desc())
        ).all()
    )
    attachments = list(
        session.scalars(
            select(UploadedAsset)
            .where(
                UploadedAsset.patient_id == encounter.patient_id,
                UploadedAsset.encounter_id == encounter.id,
            )
            .order_by(UploadedAsset.created_at.desc())
        ).all()
    )
    runs = list(
        session.scalars(
            select(AnalysisRun)
            .where(AnalysisRun.encounter_id == encounter.id)
            .order_by(AnalysisRun.created_at.desc())
        ).all()
    )
    return ClinicalCaseResponse(
        id=encounter.id,
        patient_id=encounter.patient_id,
        encounter_type=encounter.encounter_type,
        status=encounter.status,
        start_time=encounter.start_time,
        end_time=encounter.end_time,
        symptoms=encounter.symptoms,
        symptom_duration=encounter.symptom_duration,
        medical_history=encounter.medical_history,
        medications=encounter.medications or [],
        allergies=encounter.allergies or [],
        clinical_notes=encounter.clinical_notes,
        created_at=encounter.created_at,
        updated_at=encounter.updated_at,
        observations=observations,
        attachments=attachments,
        analysis_runs=runs,
        quality=_quality(encounter, observations, for_analysis=True),
    )


def _save_measurements(
    session: Session,
    encounter: Encounter,
    measurements: list[CaseMeasurement],
    actor_id: UUID,
) -> None:
    for existing in session.scalars(
        select(Observation).where(Observation.encounter_id == encounter.id)
    ).all():
        session.delete(existing)
    session.flush()

    clinical = ClinicalService(session)
    observed_at = datetime.now(timezone.utc)
    for measurement in measurements:
        clinical.create_observation(
            ObservationCreate(
                encounter_id=encounter.id,
                patient_id=encounter.patient_id,
                code=measurement.code,
                display_name=measurement.display_name,
                numeric_value=measurement.numeric_value,
                text_value=measurement.text_value,
                unit=measurement.unit,
                observed_at=observed_at,
                source_metadata=measurement.metadata(),
            ),
            actor_id=actor_id,
        )


def _get_accessible_case(
    session: Session,
    user: User,
    encounter_id: UUID,
) -> Encounter:
    encounter = session.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="Clinical case was not found.")
    require_patient_access(session, user, encounter.patient_id)
    return encounter


@router.get(
    "/patients/{patient_id}/cases",
    response_model=list[ClinicalCaseResponse],
    summary="List a patient's clinical cases",
)
def list_patient_cases(
    patient_id: UUID,
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_READ)),
    session: Session = Depends(get_db),
) -> list[ClinicalCaseResponse]:
    require_patient_access(session, current_user, patient_id)
    encounters = session.scalars(
        select(Encounter)
        .where(Encounter.patient_id == patient_id)
        .order_by(Encounter.start_time.desc())
    ).all()
    return [_case_response(session, encounter) for encounter in encounters]


@router.post(
    "/patients/{patient_id}/cases",
    response_model=ClinicalCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a clinical case draft",
)
def create_case(
    patient_id: UUID,
    payload: ClinicalCaseCreate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_CREATE)),
    session: Session = Depends(get_db),
) -> ClinicalCaseResponse:
    require_patient_access(session, current_user, patient_id)
    clinical = ClinicalService(session)
    try:
        encounter = clinical.create_encounter(
            data=EncounterCreate(
                patient_id=patient_id,
                encounter_type=payload.encounter_type,
                status=payload.status,
                start_time=payload.start_time or datetime.now(timezone.utc),
            ),
            actor_id=current_user.id,
        )
        encounter.symptoms = payload.symptoms
        encounter.symptom_duration = payload.symptom_duration
        encounter.medical_history = payload.medical_history
        encounter.medications = payload.medications
        encounter.allergies = payload.allergies
        encounter.clinical_notes = payload.clinical_notes
        _save_measurements(session, encounter, payload.measurements, current_user.id)
        AuditService(session).record_event(
            event_type="clinical_case.created",
            action="create",
            actor_id=current_user.id,
            resource_type="clinical_case",
            resource_id=str(encounter.id),
            description="Created a clinical case draft.",
            metadata={"patient_id": str(patient_id)},
            request=request,
        )
        session.commit()
        session.refresh(encounter)
        return _case_response(session, encounter)
    except EntityNotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/cases/{case_id}",
    response_model=ClinicalCaseResponse,
    summary="Retrieve a clinical case",
)
def get_case(
    case_id: UUID,
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_READ)),
    session: Session = Depends(get_db),
) -> ClinicalCaseResponse:
    return _case_response(session, _get_accessible_case(session, current_user, case_id))


@router.patch(
    "/cases/{case_id}",
    response_model=ClinicalCaseResponse,
    summary="Update a clinical case draft",
)
def update_case(
    case_id: UUID,
    payload: ClinicalCaseUpdate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_UPDATE)),
    session: Session = Depends(get_db),
) -> ClinicalCaseResponse:
    encounter = _get_accessible_case(session, current_user, case_id)
    if encounter.status not in {"draft", "planned", "in_progress"}:
        raise HTTPException(status_code=409, detail="Only an open clinical case can be edited.")

    changes = payload.model_dump(exclude_unset=True)
    measurements = changes.pop("measurements", None)
    for field, value in changes.items():
        setattr(encounter, field, value)
    if encounter.status == "completed" and encounter.end_time is None:
        encounter.end_time = datetime.now(timezone.utc)
    if measurements is not None:
        _save_measurements(
            session,
            encounter,
            [CaseMeasurement.model_validate(item) for item in measurements],
            current_user.id,
        )
    AuditService(session).record_event(
        event_type="clinical_case.updated",
        action="update",
        actor_id=current_user.id,
        resource_type="clinical_case",
        resource_id=str(encounter.id),
        description="Updated a clinical case.",
        request=request,
    )
    session.commit()
    session.refresh(encounter)
    return _case_response(session, encounter)


def _validate_case_for_analysis(
    session: Session,
    encounter: Encounter,
) -> ClinicalCaseQuality:
    observations = list(
        session.scalars(select(Observation).where(Observation.encounter_id == encounter.id)).all()
    )
    quality = _quality(encounter, observations, for_analysis=True)
    if quality.blocking_errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Case validation must be resolved before analysis.", "errors": quality.blocking_errors},
        )
    return quality


def _validate_saved_run_input(session: Session, run: AnalysisRun) -> None:
    if not isinstance(run.retry_payload, dict):
        raise HTTPException(status_code=422, detail="Complete the analysis inputs before submitting this draft.")

    if run.model_name == TABULAR_MODEL_NAME:
        try:
            TabularInferenceRequest.model_validate(
                {**run.retry_payload, "encounter_id": str(run.encounter_id)}
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail={"message": "Complete the required tabular inputs before submission.", "errors": exc.errors()},
            ) from exc
        return

    if run.model_name == ImagingMLService.MODEL_NAME:
        try:
            asset_id = UUID(str(run.retry_payload.get("asset_id")))
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail="Attach a PNG or JPEG image before submission.") from exc
        asset = session.get(UploadedAsset, asset_id)
        if (
            asset is None
            or asset.patient_id != run.patient_id
            or asset.encounter_id != run.encounter_id
        ):
            raise HTTPException(status_code=422, detail="The imaging asset is not attached to this case.")
        if asset.media_type not in {"image/png", "image/jpeg"}:
            raise HTTPException(status_code=422, detail="Imaging research supports PNG and JPEG attachments only.")
        return

    raise HTTPException(status_code=503, detail="The requested research service is unavailable.")


def _run_analysis(
    *,
    session: Session,
    run: AnalysisRun,
    actor_id: UUID,
) -> AnalysisRun:
    clinical = ClinicalService(session)
    if run.retry_payload is None or not isinstance(run.retry_payload, dict):
        raise HTTPException(status_code=409, detail="This analysis run has no saved input to submit.")

    try:
        if run.model_name == TABULAR_MODEL_NAME:
            raw_input = dict(run.retry_payload)
            raw_input["encounter_id"] = str(run.encounter_id)
            request_data = TabularInferenceRequest.model_validate(raw_input)
            service = TabularMLService(session)
            run.model_version = service.predictor.model_version
            result = service.execute_patient_tabular_analysis(
                patient_id=run.patient_id,
                request_data=request_data,
                actor_id=actor_id,
                run_id=run.id,
                before_inference=session.commit,
            )
        elif run.model_name == ImagingMLService.MODEL_NAME:
            result = ImagingMLService(session).execute_patient_imaging_analysis(
                patient_id=run.patient_id,
                asset_id=UUID(str(run.retry_payload["asset_id"])),
                encounter_id=run.encounter_id,
                generate_heatmap=bool(run.retry_payload.get("generate_heatmap", False)),
                heatmap_label=str(run.retry_payload.get("heatmap_label", "Pneumonia")),
                actor_id=actor_id,
                run_id=run.id,
                before_inference=session.commit,
            )
        else:
            raise HTTPException(status_code=503, detail="The requested research service is unavailable.")
        if result.status == "completed":
            result = clinical.update_analysis_status(
                result.id,
                status="needs_review",
                actor_id=actor_id,
            )
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Clinical workspace analysis run %s could not execute.", run.id)
        session.rollback()
        failed = session.get(AnalysisRun, run.id)
        if failed is not None and failed.status in {"draft", "queued", "running"}:
            clinical = ClinicalService(session)
            if failed.status == "draft":
                clinical.update_analysis_status(
                    failed.id,
                    status="queued",
                    actor_id=actor_id,
                )
            clinical.update_analysis_status(
                failed.id,
                status="failed",
                error_message="Research service is unavailable; retry after service recovery.",
                completed_at=datetime.now(timezone.utc),
                actor_id=actor_id,
            )
            session.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Research service is unavailable; no analysis result was produced.",
        ) from exc


@router.post(
    "/cases/{case_id}/analysis-runs",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or submit a clinical case analysis",
)
def create_case_analysis(
    case_id: UUID,
    payload: ClinicalCaseAnalysisRequest,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ANALYSIS_EXECUTE)),
    session: Session = Depends(get_db),
) -> AnalysisRunResponse:
    encounter = _get_accessible_case(session, current_user, case_id)
    if payload.submit_now:
        _validate_case_for_analysis(session, encounter)

    if payload.analysis_type == "tabular":
        model_name = TABULAR_MODEL_NAME
        model_version = TABULAR_MODEL_VERSION
        asset_id = None
        retry_payload = (
            payload.tabular_input.model_dump(exclude_unset=True)
            if payload.tabular_input is not None
            else {}
        )
        parameters: dict[str, Any] | None = {"inputs": retry_payload}
        if payload.submit_now:
            try:
                tabular = TabularInferenceRequest.model_validate(
                    {**retry_payload, "encounter_id": str(encounter.id)}
                )
            except ValidationError as exc:
                raise HTTPException(
                    status_code=422,
                    detail={"message": "Complete the required tabular inputs before submission.", "errors": exc.errors()},
                ) from exc
            retry_payload = tabular.model_dump(mode="json", exclude={"encounter_id", "parameters"})
            parameters = tabular.parameters
    else:
        model_name = ImagingMLService.MODEL_NAME
        model_version = ImagingMLService.MODEL_VERSION
        asset_id = payload.asset_id
        if asset_id is not None:
            asset = session.get(UploadedAsset, asset_id)
            if (
                asset is None
                or asset.patient_id != encounter.patient_id
                or asset.encounter_id != encounter.id
            ):
                raise HTTPException(status_code=422, detail="The imaging asset is not attached to this case.")
            if asset.media_type not in {"image/png", "image/jpeg"}:
                raise HTTPException(status_code=422, detail="Imaging research supports PNG and JPEG attachments only.")
        retry_payload = {
            "asset_id": str(asset_id) if asset_id is not None else None,
            "generate_heatmap": payload.generate_heatmap,
            "heatmap_label": payload.heatmap_label,
        }
        parameters = {
            "asset_id": str(asset_id) if asset_id is not None else None,
            "generate_heatmap": payload.generate_heatmap,
            "heatmap_label": payload.heatmap_label,
            "research_only": True,
        }

    if payload.submit_now and payload.analysis_type == "imaging" and asset_id is None:
        raise HTTPException(status_code=422, detail="Attach a PNG or JPEG image before submission.")

    active = session.scalar(
        select(AnalysisRun.id).where(
            AnalysisRun.encounter_id == encounter.id,
            AnalysisRun.model_name == model_name,
            AnalysisRun.status.in_(("queued", "running")),
        )
    )
    if active is not None:
        raise HTTPException(status_code=409, detail="An analysis for this case and model is already active.")

    clinical = ClinicalService(session)
    try:
        run = session.scalar(
            select(AnalysisRun)
            .where(
                AnalysisRun.encounter_id == encounter.id,
                AnalysisRun.model_name == model_name,
                AnalysisRun.status == "draft",
            )
            .order_by(AnalysisRun.created_at.desc())
        )
        is_new = run is None
        if run is None:
            run = clinical.create_analysis_run(
                data=AnalysisRunCreate(
                    patient_id=encounter.patient_id,
                    encounter_id=encounter.id,
                    asset_id=asset_id,
                    model_name=model_name,
                    model_version=model_version,
                    parameters=parameters,
                ),
                actor_id=current_user.id,
                initial_status="draft",
            )
        else:
            run.asset_id = asset_id
            run.model_version = model_version
            run.parameters = parameters
        run.retry_payload = retry_payload
        if payload.submit_now:
            clinical.update_analysis_status(run.id, status="queued", actor_id=current_user.id)
            encounter.status = "in_progress"
            session.flush()
        AuditService(session).record_event(
            event_type="clinical_case.analysis_draft_created" if is_new else "clinical_case.analysis_draft_updated",
            action="create" if is_new else "update",
            actor_id=current_user.id,
            resource_type="analysis_run",
            resource_id=str(run.id),
            description="Saved a research analysis draft.",
            metadata={"case_id": str(encounter.id), "model_name": model_name},
            request=request,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="An analysis for this case and model is already active.") from exc

    if payload.submit_now:
        run = _run_analysis(session=session, run=run, actor_id=current_user.id)
        session.commit()
    return AnalysisRunResponse.model_validate(run)


@router.get(
    "/analysis-runs/{run_id}",
    response_model=AnalysisRunResponse,
    summary="Retrieve an analysis run",
)
def get_case_analysis(
    run_id: UUID,
    current_user: User = Depends(require_permission(Permission.ANALYSIS_READ)),
    session: Session = Depends(get_db),
) -> AnalysisRunResponse:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run was not found.")
    require_patient_access(session, current_user, run.patient_id)
    return AnalysisRunResponse.model_validate(run)


@router.post(
    "/analysis-runs/{run_id}/submit",
    response_model=AnalysisRunResponse,
    summary="Submit a saved analysis draft",
)
def submit_case_analysis(
    run_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ANALYSIS_EXECUTE)),
    session: Session = Depends(get_db),
) -> AnalysisRunResponse:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run was not found.")
    require_patient_access(session, current_user, run.patient_id)
    if run.status != "draft":
        raise HTTPException(status_code=409, detail=f"Cannot submit an analysis in '{run.status}' state.")
    if run.encounter_id is None:
        raise HTTPException(status_code=409, detail="This run is not associated with a clinical case.")
    encounter = _get_accessible_case(session, current_user, run.encounter_id)
    _validate_case_for_analysis(session, encounter)
    _validate_saved_run_input(session, run)
    try:
        ClinicalService(session).update_analysis_status(
            run.id,
            status="queued",
            actor_id=current_user.id,
        )
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=409, detail="An analysis for this case and model is already active.") from exc

    run = _run_analysis(session=session, run=run, actor_id=current_user.id)
    AuditService(session).record_event(
        event_type="clinical_case.analysis_submitted",
        action="execute",
        actor_id=current_user.id,
        resource_type="analysis_run",
        resource_id=str(run.id),
        description="Submitted a saved research analysis run.",
        request=request,
    )
    session.commit()
    return AnalysisRunResponse.model_validate(run)


@router.post(
    "/analysis-runs/{run_id}/retry",
    response_model=AnalysisRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Retry an eligible failed analysis",
)
def retry_case_analysis(
    run_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ANALYSIS_EXECUTE)),
    session: Session = Depends(get_db),
) -> AnalysisRunResponse:
    previous = session.get(AnalysisRun, run_id)
    if previous is None:
        raise HTTPException(status_code=404, detail="Analysis run was not found.")
    require_patient_access(session, current_user, previous.patient_id)
    if previous.status != "failed" or previous.retry_payload is None:
        raise HTTPException(status_code=409, detail="Only failed runs with saved inputs can be retried.")
    if previous.encounter_id is None:
        raise HTTPException(status_code=409, detail="This run is not associated with a clinical case.")
    encounter = _get_accessible_case(session, current_user, previous.encounter_id)
    _validate_case_for_analysis(session, encounter)
    _validate_saved_run_input(session, previous)

    active = session.scalar(
        select(AnalysisRun.id).where(
            AnalysisRun.encounter_id == previous.encounter_id,
            AnalysisRun.model_name == previous.model_name,
            AnalysisRun.status.in_(("queued", "running")),
        )
    )
    if active is not None:
        raise HTTPException(status_code=409, detail="An analysis for this case and model is already active.")

    retry = ClinicalService(session).create_analysis_run(
        data=AnalysisRunCreate(
            patient_id=previous.patient_id,
            encounter_id=previous.encounter_id,
            asset_id=previous.asset_id,
            model_name=previous.model_name,
            model_version=previous.model_version,
            parameters={**(previous.parameters or {}), "retry_of_run_id": str(previous.id)},
        ),
        actor_id=current_user.id,
        initial_status="draft",
    )
    retry.retry_payload = dict(previous.retry_payload)
    previous.retry_count += 1
    AuditService(session).record_event(
        event_type="analysis.retry_created",
        action="create",
        actor_id=current_user.id,
        resource_type="analysis_run",
        resource_id=str(retry.id),
        description="Created a new analysis run from an eligible failed run.",
        metadata={"retry_of_run_id": str(previous.id)},
        request=request,
    )
    session.commit()
    ClinicalService(session).update_analysis_status(
        retry.id,
        status="queued",
        actor_id=current_user.id,
    )
    session.commit()
    retry = _run_analysis(session=session, run=retry, actor_id=current_user.id)
    session.commit()
    return AnalysisRunResponse.model_validate(retry)


@router.post(
    "/analysis-runs/{run_id}/review",
    response_model=AnalysisRunResponse,
    summary="Record qualified human review of a result",
)
def review_case_analysis(
    run_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ANALYSIS_REVIEW)),
    session: Session = Depends(get_db),
) -> AnalysisRunResponse:
    run = session.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run was not found.")
    require_patient_access(session, current_user, run.patient_id)
    if run.status != "needs_review":
        raise HTTPException(status_code=409, detail="Only results awaiting review can be reviewed.")
    updated = ClinicalService(session).update_analysis_status(
        run.id,
        status="completed",
        actor_id=current_user.id,
    )
    AuditService(session).record_event(
        event_type="analysis.human_reviewed",
        action="review",
        actor_id=current_user.id,
        resource_type="analysis_run",
        resource_id=str(run.id),
        description="A qualified reviewer recorded review of this research result.",
        metadata={"patient_id": str(run.patient_id), "case_id": str(run.encounter_id)},
        request=request,
    )
    session.commit()
    return AnalysisRunResponse.model_validate(updated)
