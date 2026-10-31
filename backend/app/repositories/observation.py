"""Arogya AI — Observation Repository.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Encapsulates database operations for clinical observations, vital signs, and measurements.
"""

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID
from sqlalchemy import func, select

from backend.app.db.models import Observation
from backend.app.repositories.base import BaseRepository


class ObservationRepository(BaseRepository[Observation]):
    """Data access repository for clinical observations."""

    def get_by_id(self, observation_id: UUID) -> Observation | None:
        """Retrieve an observation by primary key UUID."""
        return self.session.get(Observation, observation_id)

    def create(
        self,
        encounter_id: UUID,
        patient_id: UUID,
        code: str,
        display_name: str,
        observed_at: datetime,
        numeric_value: float | None = None,
        text_value: str | None = None,
        unit: str | None = None,
        source_metadata: dict[str, Any] | None = None,
    ) -> Observation:
        """Instantiate and persist a new clinical observation."""
        observation = Observation(
            encounter_id=encounter_id,
            patient_id=patient_id,
            code=code.strip(),
            display_name=display_name.strip(),
            observed_at=observed_at,
            numeric_value=numeric_value,
            text_value=text_value.strip() if text_value else None,
            unit=unit.strip() if unit else None,
            source_metadata=source_metadata,
        )
        self.session.add(observation)
        self.session.flush()
        return observation

    def list_by_encounter(
        self,
        encounter_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Observation]:
        """Retrieve bounded list of observations recorded during an encounter."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = (
            select(Observation)
            .where(Observation.encounter_id == encounter_id)
            .order_by(Observation.observed_at.asc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def list_by_patient(
        self,
        patient_id: UUID,
        code: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Observation]:
        """Retrieve bounded longitudinal observations for a patient, optionally filtered by code."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = select(Observation).where(Observation.patient_id == patient_id)

        if code is not None:
            stmt = stmt.where(Observation.code == code.strip())

        stmt = (
            stmt.order_by(Observation.observed_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def count_by_patient(
        self,
        patient_id: UUID,
        code: str | None = None,
    ) -> int:
        """Count total observations recorded for a patient."""
        stmt = select(func.count(Observation.id)).where(Observation.patient_id == patient_id)
        if code is not None:
            stmt = stmt.where(Observation.code == code.strip())
        return self.session.scalar(stmt) or 0

    def count_by_encounter(self, encounter_id: UUID) -> int:
        """Count total observations recorded during an encounter."""
        stmt = select(func.count(Observation.id)).where(Observation.encounter_id == encounter_id)
        return self.session.scalar(stmt) or 0

