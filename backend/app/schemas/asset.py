"""Arogya AI - Uploaded Asset Metadata API Schemas.

Module 3, Phase 3.4 & Module 7, Phase 7.5: Uploaded Asset Contracts.
Defines contracts for uploaded asset metadata (e.g. imaging, clinical documents).
Strictly separates metadata tracking from binary storage:
- Binary payloads are handled by dedicated storage services; JSON schemas manage metadata only.
- Untrusted clients cannot specify internal server storage_path locators.
- Metadata validation does not imply clinical validity or verification.
"""

from datetime import datetime
from uuid import UUID
from pydantic import Field
from backend.app.schemas.common import BaseSchema, ORMModel


class AssetMetadataBase(BaseSchema):
    """Base schema attributes for uploaded asset metadata."""

    original_filename: str = Field(
        min_length=1,
        max_length=255,
        description="Sanitized display filename of uploaded asset",
        examples=["chest_xray_pa.png"],
    )
    media_type: str = Field(
        min_length=3,
        max_length=128,
        description="MIME media classification (e.g. 'image/png', 'application/dicom')",
        examples=["image/png"],
    )
    file_size_bytes: int = Field(
        gt=0,
        description="Size of binary payload in bytes (must be greater than 0)",
        examples=[4194304],
    )
    checksum_sha256: str = Field(
        pattern=r"^[a-fA-F0-9]{64}$",
        description="SHA-256 cryptographic hexadecimal digest for integrity verification",
        examples=["e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"],
    )


class AssetMetadataCreate(AssetMetadataBase):
    """Request contract for registering uploaded asset metadata.

    Security Notice:
    - storage_path is strictly excluded; internal storage locators are assigned by the server.
    """

    patient_id: UUID = Field(
        description="Identifier of owning patient record",
    )
    encounter_id: UUID | None = Field(
        default=None,
        description="Optional identifier of associated encounter",
    )


class AssetMetadataResponse(AssetMetadataBase, ORMModel):
    """Response contract representing registered asset metadata."""

    id: UUID = Field(
        description="Unique asset identifier",
    )
    patient_id: UUID = Field(
        description="Identifier of owning patient",
    )
    encounter_id: UUID | None = Field(
        default=None,
        description="Identifier of associated encounter",
    )
    storage_path: str = Field(
        description="Server-managed opaque storage reference",
    )
    created_at: datetime = Field(
        description="Asset registration timestamp in UTC",
    )


# Alias for Module 7 naming consistency
UploadedAssetResponse = AssetMetadataResponse

__all__ = [
    "AssetMetadataBase",
    "AssetMetadataCreate",
    "AssetMetadataResponse",
    "UploadedAssetResponse",
]
