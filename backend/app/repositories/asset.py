"""Arogya AI — Asset Repository.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Encapsulates database operations for uploaded asset metadata, checksums, and storage locators.
"""

from typing import Sequence
from uuid import UUID
from sqlalchemy import func, select

from backend.app.db.models import UploadedAsset
from backend.app.repositories.base import BaseRepository


class AssetRepository(BaseRepository[UploadedAsset]):
    """Data access repository for uploaded file and imaging asset metadata."""

    def get_by_id(self, asset_id: UUID) -> UploadedAsset | None:
        """Retrieve asset metadata record by primary key UUID."""
        return self.session.get(UploadedAsset, asset_id)

    def get_by_storage_path(self, storage_path: str) -> UploadedAsset | None:
        """Retrieve asset metadata record by unique storage path."""
        stmt = select(UploadedAsset).where(UploadedAsset.storage_path == storage_path.strip())
        return self.session.scalar(stmt)

    def create(
        self,
        patient_id: UUID,
        original_filename: str,
        media_type: str,
        file_size_bytes: int,
        storage_path: str,
        checksum_sha256: str,
        encounter_id: UUID | None = None,
    ) -> UploadedAsset:
        """Instantiate and persist a new asset metadata record."""
        asset = UploadedAsset(
            patient_id=patient_id,
            encounter_id=encounter_id,
            original_filename=original_filename.strip(),
            media_type=media_type.strip().lower(),
            file_size_bytes=file_size_bytes,
            storage_path=storage_path.strip(),
            checksum_sha256=checksum_sha256.strip().lower(),
        )
        self.session.add(asset)
        self.session.flush()
        return asset

    def list_by_patient(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[UploadedAsset]:
        """Retrieve bounded list of uploaded assets belonging to a patient."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = (
            select(UploadedAsset)
            .where(UploadedAsset.patient_id == patient_id)
            .order_by(UploadedAsset.created_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def count_by_patient(self, patient_id: UUID) -> int:
        """Count total assets recorded for a patient."""
        stmt = select(func.count(UploadedAsset.id)).where(UploadedAsset.patient_id == patient_id)
        return self.session.scalar(stmt) or 0
