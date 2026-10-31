"""Arogya AI — Uploaded Asset & File Handling Endpoints.

Module 7, Phase 7.5 & 7.6: Safe File Uploads & Storage.
Exposes endpoints for:
- Authenticated clinical asset uploads (images, PDFs, DICOMs)
- Asset metadata retrieval
- Authenticated, resource-authorized binary downloads
- Cross-patient validation preventing unauthorized asset attachments
"""

import logging
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.models import Encounter, Patient, UploadedAsset, User
from backend.app.db.session import get_db
from backend.app.errors import ErrorResponse
from backend.app.schemas.asset import UploadedAssetResponse
from backend.app.security.dependencies import require_permission
from backend.app.security.roles import Permission
from backend.app.services.audit import AuditService
from backend.app.services.storage import FileValidationError, StorageService
from backend.app.settings import Settings, get_settings

logger = logging.getLogger("arogya.api.assets")

router = APIRouter(
    tags=["Asset & File Handling"],
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
            "description": "Target patient, encounter, or asset not found",
        },
        422: {
            "model": ErrorResponse,
            "description": "File validation or cross-patient consistency error",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error envelope",
        },
    },
)


@router.post(
    "/assets/upload",
    response_model=UploadedAssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Clinical Asset or Radiograph",
    description="Validate file format, size, and magic-byte signature, store safely, and persist asset metadata.",
)
async def upload_asset(
    request: Request,
    file: UploadFile = File(..., description="Binary clinical file or imaging payload"),
    patient_id: uuid.UUID = Form(..., description="ID of patient associated with asset"),
    encounter_id: uuid.UUID | None = Form(default=None, description="Optional ID of associated clinical encounter"),
    current_user: User = Depends(require_permission(Permission.ASSET_UPLOAD)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> UploadedAssetResponse:
    """Validate and ingest a clinical file attachment under strict security boundaries."""
    # 1. Verify target patient exists
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found",
        )

    # 2. Cross-patient validation: verify encounter belongs to this patient
    if encounter_id is not None:
        encounter = db.get(Encounter, encounter_id)
        if encounter is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Encounter '{encounter_id}' not found",
            )
        if encounter.patient_id != patient_id:
            # Cross-patient boundary violation!
            AuditService(db).record_event(
                event_type="security.cross_patient_violation",
                action="denied",
                actor_id=current_user.id,
                resource_type="encounter",
                resource_id=str(encounter_id),
                description=f"Attempted to attach asset for patient {patient_id} to encounter owned by patient {encounter.patient_id}",
                request=request,
            )
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Encounter '{encounter_id}' does not belong to patient '{patient_id}'",
            )

    # 3. Read payload and inspect bounds
    try:
        file_bytes = await file.read()
    except Exception as exc:
        logger.error("Failed to read uploaded file payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to read file payload",
        ) from exc

    # 4. Safe storage and cryptographic verification
    app_settings: Settings = getattr(request.app.state, "settings", None) or settings
    try:
        relative_path, safe_name, safe_media, file_size, checksum = StorageService.validate_and_save(
            file_bytes=file_bytes,
            original_filename=file.filename or "unnamed_clinical_asset",
            media_type=file.content_type,
            storage_base_dir=app_settings.upload_storage_dir,
            max_size_bytes=app_settings.max_upload_size_bytes,
        )
    except FileValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(err),
        ) from err

    # 5. Persist metadata record in database
    asset = UploadedAsset(
        id=uuid.uuid4(),
        patient_id=patient_id,
        encounter_id=encounter_id,
        original_filename=safe_name,
        media_type=safe_media,
        file_size_bytes=file_size,
        storage_path=relative_path,
        checksum_sha256=checksum,
    )
    db.add(asset)

    # 6. Record security audit event
    AuditService(db).record_event(
        event_type="asset.uploaded",
        action="create",
        actor_id=current_user.id,
        resource_type="asset",
        resource_id=str(asset.id),
        description=f"Uploaded clinical asset '{safe_name}' ({file_size} bytes)",
        metadata={
            "patient_id": str(patient_id),
            "media_type": safe_media,
            "checksum_sha256": checksum,
        },
        request=request,
    )

    db.commit()
    db.refresh(asset)
    return UploadedAssetResponse.model_validate(asset)


@router.get(
    "/assets/{asset_id}",
    response_model=UploadedAssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Asset Metadata",
    description="Retrieve metadata for a previously uploaded clinical asset.",
)
def get_asset_metadata(
    asset_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.ASSET_READ)),
    db: Session = Depends(get_db),
) -> UploadedAssetResponse:
    """Retrieve metadata for an asset by its primary identifier."""
    asset = db.get(UploadedAsset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )
    return UploadedAssetResponse.model_validate(asset)


@router.get(
    "/assets/{asset_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download Clinical Asset Binary",
    description="Download the binary payload of an authorized clinical file or medical imaging asset.",
)
def download_asset(
    asset_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_permission(Permission.ASSET_READ)),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Serve an asset's binary payload under strict resource authorization."""
    asset = db.get(UploadedAsset, asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_id}' not found",
        )

    app_settings: Settings = getattr(request.app.state, "settings", None) or settings
    try:
        file_path = StorageService.resolve_file_path(
            asset.storage_path,
            storage_base_dir=app_settings.upload_storage_dir,
        )
    except FileValidationError as err:
        logger.error("Failed to resolve asset '%s' storage path: %s", asset_id, err)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset binary file not found on storage volume",
        ) from err

    # Record download audit event
    AuditService(db).record_event(
        event_type="asset.downloaded",
        action="read",
        actor_id=current_user.id,
        resource_type="asset",
        resource_id=str(asset.id),
        description=f"Downloaded clinical asset '{asset.original_filename}'",
        metadata={
            "patient_id": str(asset.patient_id),
            "media_type": asset.media_type,
        },
        request=request,
    )
    db.commit()

    return FileResponse(
        path=str(file_path),
        media_type=asset.media_type,
        filename=asset.original_filename,
    )


@router.get(
    "/patients/{patient_id}/assets",
    response_model=list[UploadedAssetResponse],
    status_code=status.HTTP_200_OK,
    summary="List Assets for Patient",
    description="Retrieve all clinical imaging attachments and documents associated with a patient.",
)
def list_patient_assets(
    patient_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.ASSET_READ)),
    db: Session = Depends(get_db),
) -> list[UploadedAssetResponse]:
    """List assets associated with a specific patient record."""
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found",
        )

    stmt = (
        select(UploadedAsset)
        .where(UploadedAsset.patient_id == patient_id)
        .order_by(UploadedAsset.created_at.desc())
    )
    assets = db.scalars(stmt).all()
    return [UploadedAssetResponse.model_validate(a) for a in assets]
