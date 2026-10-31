"""Arogya AI — Encounter Repository.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Encapsulates database operations for patient clinical encounters.
"""

from datetime import datetime
from typing import Sequence
from uuid import UUID
from sqlalchemy import func, select

from backend.app.db.models import Encounter
from backend.app.repositories.base import BaseRepository


class EncounterRepository(BaseRepository[Encounter]):
    """Data access repository for clinical encounters."""

    def get_by_id(self, encounter_id: UUID) -> Encounter | None:
        """Retrieve an encounter by primary key UUID."""
        return self.session.get(Encounter, encounter_id)

    def create(
        self,
        patient_id: UUID,
        start_time: datetime,
        encounter_type: str = "ambulatory",
        status: str = "in_progress",
        end_time: datetime | None = None,
    ) -> Encounter:
        """Instantiate and persist a new encounter record."""
        encounter = Encounter(
            patient_id=patient_id,
            start_time=start_time,
            end_time=end_time,
            encounter_type=encounter_type.strip().lower(),
            status=status.strip().lower(),
        )
        self.session.add(encounter)
        self.session.flush()
        return encounter

    def update(
        self,
        encounter: Encounter,
        status: str | None = None,
        end_time: datetime | None = None,
        encounter_type: str | None = None,
    ) -> Encounter:
        """Update mutable fields on an existing encounter record."""
        if status is not None:
            encounter.status = status.strip().lower()
        if end_time is not None:
            encounter.end_time = end_time
        if encounter_type is not None:
            encounter.encounter_type = encounter_type.strip().lower()

        self.session.flush()
        return encounter

    def list_by_patient(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> Sequence[Encounter]:
        """Retrieve bounded list of encounters for a specific patient."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = select(Encounter).where(Encounter.patient_id == patient_id)

        if status is not None:
            stmt = stmt.where(Encounter.status == status.strip().lower())

        stmt = (
            stmt.order_by(Encounter.start_time.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def count_by_patient(
        self,
        patient_id: UUID,
        status: str | None = None,
    ) -> int:
        """Count total encounter records for a patient."""
        stmt = select(func.count(Encounter.id)).where(Encounter.patient_id == patient_id)
        if status is not None:
            stmt = stmt.where(Encounter.status == status.strip().lower())
        return self.session.scalar(stmt) or 0
