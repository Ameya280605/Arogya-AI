"""Arogya AI — Patient Intelligence & Clinical Data Ingestion API Endpoints.

Module 6: Patient Intelligence & Module 7: Security, Identity & File Handling.
Exposes REST endpoints for:
- Patient cohort listing, search, filtering, and pagination
- Patient profile creation and updates with Pydantic validation
- Clinical encounter creation, status tracking, and timeline retrieval
- Physiological observation recording linked to encounters and patients
- Data quality completeness scoring and unit/demographic consistency evaluation
Enforces least-privilege server-side authorization and cryptographic audit logging.
"""

from typing import Sequence
from uuid import UUID
import logging
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from backend.app.db import get_db
from backend.app.db.models import User
from backend.app.errors import ErrorResponse
from backend.app.schemas.analysis import AnalysisRunResponse
from backend.app.schemas.common import PaginatedResponse
from backend.app.schemas.encounter import (
    EncounterCreate,
    EncounterCreatePayload,
    EncounterResponse,
    EncounterUpdate,
)
from backend.app.schemas.observation import (
    ObservationCreate,
    ObservationCreatePayload,
    ObservationResponse,
)
from backend.app.schemas.patient import (
    DataQualityReport,
    PatientCreate,
    PatientResponse,
    PatientTimelineResponse,
    PatientUpdate,
)
from backend.app.security.dependencies import require_permission
from backend.app.security.roles import Permission
from backend.app.services.audit import AuditService
from backend.app.services.clinical import ClinicalService
from backend.app.services.exceptions import (
    ConsistencyError,
    DuplicateEntityError,
    EntityNotFoundError,
)

logger = logging.getLogger("arogya.patients")

router = APIRouter(
    tags=["Patient Intelligence"],
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Authentication required",
        },
        403: {
            "model": ErrorResponse,
            "description": "Forbidden: insufficient permissions",
        },
        404: {
            "model": ErrorResponse,
            "description": "Requested patient or clinical entity not found",
        },
        409: {
            "model": ErrorResponse,
            "description": "Conflict or uniqueness constraint violation (e.g. duplicate MRN)",
        },
        422: {
            "model": ErrorResponse,
            "description": "Schema validation failure or cross-entity consistency violation",
        },
        500: {
            "model": ErrorResponse,
            "description": "Standard internal server error envelope",
        },
        503: {
            "model": ErrorResponse,
            "description": "Database persistence is unconfigured or unavailable",
        },
    },
)


# -----------------------------------------------------------------------------
# 6.1 & 6.2: Patient List & CRUD
# -----------------------------------------------------------------------------


@router.get(
    "/patients",
    response_model=PaginatedResponse[PatientResponse],
    status_code=status.HTTP_200_OK,
    summary="List Patient Cohort",
    description="Retrieve a paginated, filterable collection of research and synthetic patient profiles.",
)
def list_patients(
    search: str | None = Query(
        default=None,
        description="Search term to match against pseudonymous MRN",
    ),
    biological_sex: str | None = Query(
        default=None,
        description="Filter by biological sex ('male', 'female', 'other', 'unknown')",
    ),
    is_synthetic: bool | None = Query(
        default=None,
        description="Filter by synthetic vs. licensed public research designation",
    ),
    page: int = Query(default=1, ge=1, description="1-based page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Records per page"),
    current_user: User = Depends(require_permission(Permission.PATIENT_READ)),
    session: Session = Depends(get_db),
) -> PaginatedResponse[PatientResponse]:
    """List patients with search, filtering, and pagination."""
    service = ClinicalService(session)
    offset = (page - 1) * page_size
    items = service.list_patients(
        limit=page_size,
        offset=offset,
        is_synthetic=is_synthetic,
        search=search,
        biological_sex=biological_sex,
    )
    total = service.count_patients(
        is_synthetic=is_synthetic,
        search=search,
        biological_sex=biological_sex,
    )
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/patients",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Patient",
    description="Register a new research or synthetic patient profile with pseudonymous MRN.",
)
def create_patient(
    payload: PatientCreate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.PATIENT_CREATE)),
    session: Session = Depends(get_db),
) -> PatientResponse:
    """Create a new patient record with uniqueness enforcement and audit logging."""
    service = ClinicalService(session)
    try:
        patient = service.create_patient(data=payload)
        AuditService(session).record_event(
            event_type="patient.created",
            action="create",
            actor_id=current_user.id,
            resource_type="patient",
            resource_id=str(patient.id),
            description=f"Registered patient profile '{patient.mrn_pseudonym}'",
            metadata={"mrn_pseudonym": patient.mrn_pseudonym, "is_synthetic": patient.is_synthetic},
            request=request,
        )
        session.commit()
        return PatientResponse.model_validate(patient)
    except DuplicateEntityError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/patients/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Patient Profile",
    description="Retrieve demographic attributes of a patient by UUID.",
)
def get_patient(
    patient_id: UUID,
    current_user: User = Depends(require_permission(Permission.PATIENT_READ)),
    session: Session = Depends(get_db),
) -> PatientResponse:
    """Retrieve patient record by ID."""
    service = ClinicalService(session)
    patient = service.get_patient(patient_id=patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found.",
        )
    return PatientResponse.model_validate(patient)


@router.patch(
    "/patients/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Patient Profile",
    description="Update mutable demographic fields on a patient profile.",
)
def update_patient(
    patient_id: UUID,
    payload: PatientUpdate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.PATIENT_UPDATE)),
    session: Session = Depends(get_db),
) -> PatientResponse:
    """Update patient demographic attributes."""
    service = ClinicalService(session)
    try:
        updated = service.update_patient(patient_id=patient_id, data=payload)
        AuditService(session).record_event(
            event_type="patient.updated",
            action="update",
            actor_id=current_user.id,
            resource_type="patient",
            resource_id=str(patient_id),
            description=f"Updated patient profile '{updated.mrn_pseudonym}'",
            request=request,
        )
        session.commit()
        return PatientResponse.model_validate(updated)
    except EntityNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# -----------------------------------------------------------------------------
# 6.3 & 6.5: Data Quality & Timeline
# -----------------------------------------------------------------------------


@router.get(
    "/patients/{patient_id}/quality",
    response_model=DataQualityReport,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Patient Data Quality",
    description="Compute data completeness score and evaluate demographic/unit consistency warnings.",
)
def get_patient_data_quality(
    patient_id: UUID,
    current_user: User = Depends(require_permission(Permission.PATIENT_READ)),
    session: Session = Depends(get_db),
) -> DataQualityReport:
    """Compute demographic completeness, clinical continuity, and measurement unit integrity."""
    service = ClinicalService(session)
    try:
        return service.evaluate_data_quality(patient_id=patient_id)
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/patients/{patient_id}/timeline",
    response_model=PatientTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Patient Longitudinal Timeline",
    description="Retrieve a unified chronological event stream of encounters, vitals, and analyses.",
)
def get_patient_timeline(
    patient_id: UUID,
    limit: int = Query(default=50, ge=1, le=200, description="Max timeline events to return"),
    current_user: User = Depends(require_permission(Permission.PATIENT_READ)),
    session: Session = Depends(get_db),
) -> PatientTimelineResponse:
    """Retrieve chronological unified event timeline for a patient."""
    service = ClinicalService(session)
    try:
        return service.get_patient_timeline(patient_id=patient_id, limit=limit)
    except EntityNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# -----------------------------------------------------------------------------
# 6.4: Encounters
# -----------------------------------------------------------------------------


@router.get(
    "/patients/{patient_id}/encounters",
    response_model=PaginatedResponse[EncounterResponse],
    status_code=status.HTTP_200_OK,
    summary="List Patient Encounters",
    description="Retrieve all clinical encounters recorded for a target patient.",
)
def list_patient_encounters(
    patient_id: UUID,
    status_filter: str | None = Query(default=None, alias="status", description="Filter by encounter status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_READ)),
    session: Session = Depends(get_db),
) -> PaginatedResponse[EncounterResponse]:
    """List encounters for a patient."""
    service = ClinicalService(session)
    if service.get_patient(patient_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found.",
        )

    offset = (page - 1) * page_size
    items = service.list_encounters_by_patient(
        patient_id=patient_id,
        limit=page_size,
        offset=offset,
        status=status_filter,
    )
    total = service.count_encounters_by_patient(patient_id=patient_id, status=status_filter)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/patients/{patient_id}/encounters",
    response_model=EncounterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Clinical Encounter",
    description="Record a clinical encounter scoped to a specific patient.",
)
def create_patient_encounter(
    patient_id: UUID,
    payload: EncounterCreatePayload,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_CREATE)),
    session: Session = Depends(get_db),
) -> EncounterResponse:
    """Create a new clinical encounter associated with a patient."""
    service = ClinicalService(session)
    encounter_data = EncounterCreate(
        patient_id=patient_id,
        encounter_type=payload.encounter_type,
        status=payload.status,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    try:
        encounter = service.create_encounter(data=encounter_data)
        AuditService(session).record_event(
            event_type="encounter.created",
            action="create",
            actor_id=current_user.id,
            resource_type="encounter",
            resource_id=str(encounter.id),
            description=f"Created clinical encounter for patient '{patient_id}'",
            metadata={"patient_id": str(patient_id), "encounter_type": payload.encounter_type},
            request=request,
        )
        session.commit()
        return EncounterResponse.model_validate(encounter)
    except EntityNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/encounters/{encounter_id}",
    response_model=EncounterResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Encounter Details",
    description="Retrieve a single clinical encounter by UUID.",
)
def get_encounter(
    encounter_id: UUID,
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_READ)),
    session: Session = Depends(get_db),
) -> EncounterResponse:
    """Retrieve encounter details."""
    service = ClinicalService(session)
    encounter = service.get_encounter(encounter_id=encounter_id)
    if encounter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter with identifier '{encounter_id}' was not found.",
        )
    return EncounterResponse.model_validate(encounter)


@router.patch(
    "/encounters/{encounter_id}",
    response_model=EncounterResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Encounter",
    description="Update encounter lifecycle status, type, or conclusion timestamp.",
)
def update_encounter(
    encounter_id: UUID,
    payload: EncounterUpdate,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ENCOUNTER_UPDATE)),
    session: Session = Depends(get_db),
) -> EncounterResponse:
    """Update encounter status or conclusion time."""
    service = ClinicalService(session)
    try:
        updated = service.update_encounter(encounter_id=encounter_id, data=payload)
        AuditService(session).record_event(
            event_type="encounter.updated",
            action="update",
            actor_id=current_user.id,
            resource_type="encounter",
            resource_id=str(encounter_id),
            description=f"Updated encounter '{encounter_id}' details",
            request=request,
        )
        session.commit()
        return EncounterResponse.model_validate(updated)
    except EntityNotFoundError as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# -----------------------------------------------------------------------------
# Observations & Analysis Results
# -----------------------------------------------------------------------------


@router.get(
    "/encounters/{encounter_id}/observations",
    response_model=PaginatedResponse[ObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Observations in Encounter",
    description="Retrieve all clinical observations and vitals acquired during an encounter.",
)
def list_encounter_observations(
    encounter_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_permission(Permission.OBSERVATION_READ)),
    session: Session = Depends(get_db),
) -> PaginatedResponse[ObservationResponse]:
    """List observations for an encounter."""
    service = ClinicalService(session)
    if service.get_encounter(encounter_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter with identifier '{encounter_id}' was not found.",
        )

    offset = (page - 1) * page_size
    items = service.list_observations_by_encounter(
        encounter_id=encounter_id,
        limit=page_size,
        offset=offset,
    )
    total = service.count_observations_by_encounter(encounter_id=encounter_id)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/encounters/{encounter_id}/observations",
    response_model=ObservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Clinical Observation",
    description="Record a physiological vital sign or lab measurement acquired during an encounter.",
)
def create_encounter_observation(
    encounter_id: UUID,
    payload: ObservationCreatePayload,
    request: Request,
    current_user: User = Depends(require_permission(Permission.OBSERVATION_CREATE)),
    session: Session = Depends(get_db),
) -> ObservationResponse:
    """Record an observation linked to an encounter."""
    service = ClinicalService(session)
    encounter = service.get_encounter(encounter_id)
    if encounter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Encounter with identifier '{encounter_id}' was not found.",
        )

    obs_data = ObservationCreate(
        encounter_id=encounter_id,
        patient_id=encounter.patient_id,
        code=payload.code,
        display_name=payload.display_name,
        numeric_value=payload.numeric_value,
        text_value=payload.text_value,
        unit=payload.unit,
        observed_at=payload.observed_at,
        source_metadata=payload.source_metadata,
    )
    try:
        obs = service.create_observation(data=obs_data)
        AuditService(session).record_event(
            event_type="observation.created",
            action="create",
            actor_id=current_user.id,
            resource_type="observation",
            resource_id=str(obs.id),
            description=f"Recorded observation '{obs.code}' for encounter '{encounter_id}'",
            metadata={"encounter_id": str(encounter_id), "code": payload.code},
            request=request,
        )
        session.commit()
        return ObservationResponse.model_validate(obs)
    except (ConsistencyError, EntityNotFoundError) as exc:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/patients/{patient_id}/observations",
    response_model=PaginatedResponse[ObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Patient Longitudinal Observations",
    description="Retrieve longitudinal observations across encounters for a patient.",
)
def list_patient_observations(
    patient_id: UUID,
    code: str | None = Query(default=None, description="Optional LOINC concept filter"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.OBSERVATION_READ)),
    session: Session = Depends(get_db),
) -> PaginatedResponse[ObservationResponse]:
    """List longitudinal observations for a patient."""
    service = ClinicalService(session)
    if service.get_patient(patient_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found.",
        )

    offset = (page - 1) * page_size
    items = service.list_observations_by_patient(
        patient_id=patient_id,
        code=code,
        limit=page_size,
        offset=offset,
    )
    total = service.count_observations_by_patient(patient_id=patient_id, code=code)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/patients/{patient_id}/analysis-runs",
    response_model=PaginatedResponse[AnalysisRunResponse],
    status_code=status.HTTP_200_OK,
    summary="List Patient Analysis Runs",
    description="Retrieve research AI analysis runs and evaluations associated with a patient.",
)
def list_patient_analysis_runs(
    patient_id: UUID,
    status_filter: str | None = Query(default=None, alias="status", description="Filter by run status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(require_permission(Permission.ANALYSIS_READ)),
    session: Session = Depends(get_db),
) -> PaginatedResponse[AnalysisRunResponse]:
    """List AI analysis runs for a patient."""
    service = ClinicalService(session)
    if service.get_patient(patient_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with identifier '{patient_id}' was not found.",
        )

    offset = (page - 1) * page_size
    items = service.list_analysis_runs_by_patient(
        patient_id=patient_id,
        limit=page_size,
        offset=offset,
        status=status_filter,
    )
    total = service.count_analysis_runs_by_patient(patient_id=patient_id, status=status_filter)
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )
