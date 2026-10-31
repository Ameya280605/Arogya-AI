"""Arogya AI — Analysis Run Repository.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Encapsulates database operations for AI analysis executions and research evaluations.
"""

from datetime import datetime
from typing import Any, Sequence
from uuid import UUID
from sqlalchemy import func, select

from backend.app.db.models import AnalysisRun
from backend.app.repositories.base import BaseRepository


class AnalysisRepository(BaseRepository[AnalysisRun]):
    """Data access repository for AI model analysis runs."""

    def get_by_id(self, run_id: UUID) -> AnalysisRun | None:
        """Retrieve an analysis run by primary key UUID."""
        return self.session.get(AnalysisRun, run_id)

    def create(
        self,
        patient_id: UUID,
        model_name: str,
        model_version: str,
        status: str = "queued",
        encounter_id: UUID | None = None,
        asset_id: UUID | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> AnalysisRun:
        """Instantiate and persist a new analysis run record."""
        run = AnalysisRun(
            patient_id=patient_id,
            encounter_id=encounter_id,
            asset_id=asset_id,
            model_name=model_name.strip(),
            model_version=model_version.strip(),
            status=status.strip().lower(),
            parameters=parameters,
        )
        self.session.add(run)
        self.session.flush()
        return run

    def update_status(
        self,
        run: AnalysisRun,
        status: str,
        results_summary: dict[str, Any] | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> AnalysisRun:
        """Update execution lifecycle status and evaluation output containers."""
        run.status = status.strip().lower()
        if results_summary is not None:
            run.results_summary = results_summary
        if error_message is not None:
            run.error_message = error_message
        if started_at is not None:
            run.started_at = started_at
        if completed_at is not None:
            run.completed_at = completed_at

        self.session.flush()
        return run

    def list_by_patient(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> Sequence[AnalysisRun]:
        """Retrieve bounded list of analysis runs associated with a patient."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = select(AnalysisRun).where(AnalysisRun.patient_id == patient_id)

        if status is not None:
            stmt = stmt.where(AnalysisRun.status == status.strip().lower())

        stmt = (
            stmt.order_by(AnalysisRun.created_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def list_by_encounter(
        self,
        encounter_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[AnalysisRun]:
        """Retrieve bounded list of analysis runs associated with an encounter."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = (
            select(AnalysisRun)
            .where(AnalysisRun.encounter_id == encounter_id)
            .order_by(AnalysisRun.created_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def count_by_patient(self, patient_id: UUID, status: str | None = None) -> int:
        """Count total analysis runs for a patient."""
        stmt = select(func.count(AnalysisRun.id)).where(AnalysisRun.patient_id == patient_id)
        if status is not None:
            stmt = stmt.where(AnalysisRun.status == status.strip().lower())
        return self.session.scalar(stmt) or 0
