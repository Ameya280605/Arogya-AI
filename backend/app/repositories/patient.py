"""Arogya AI — Patient Repository.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Encapsulates database operations for patient research cohorts and synthetic profiles.
"""

from datetime import date
from typing import Sequence
from uuid import UUID
from sqlalchemy import func, select

from backend.app.db.models import Patient
from backend.app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    """Data access repository for patient entities."""

    def get_by_id(self, patient_id: UUID) -> Patient | None:
        """Retrieve a patient by primary key UUID."""
        return self.session.get(Patient, patient_id)

    def get_by_mrn(self, mrn: str) -> Patient | None:
        """Retrieve a patient by pseudonymous medical record number (mrn_pseudonym)."""
        stmt = select(Patient).where(Patient.mrn_pseudonym == mrn.strip())
        return self.session.scalar(stmt)

    def create(
        self,
        mrn_pseudonym: str,
        birth_date: date | None = None,
        biological_sex: str | None = None,
        is_synthetic: bool = True,
    ) -> Patient:
        """Instantiate and persist a new patient profile record."""
        patient = Patient(
            mrn_pseudonym=mrn_pseudonym.strip(),
            birth_date=birth_date,
            biological_sex=biological_sex.strip().lower() if biological_sex else None,
            is_synthetic=is_synthetic,
        )
        self.session.add(patient)
        self.session.flush()
        return patient

    def update(
        self,
        patient: Patient,
        birth_date: date | None = None,
        biological_sex: str | None = None,
        is_synthetic: bool | None = None,
    ) -> Patient:
        """Update mutable demographic fields on an existing patient record."""
        if birth_date is not None:
            patient.birth_date = birth_date
        if biological_sex is not None:
            patient.biological_sex = biological_sex.strip().lower()
        if is_synthetic is not None:
            patient.is_synthetic = is_synthetic

        self.session.flush()
        return patient

    def list_patients(
        self,
        limit: int = 100,
        offset: int = 0,
        is_synthetic: bool | None = None,
        search: str | None = None,
        biological_sex: str | None = None,
    ) -> Sequence[Patient]:
        """Retrieve a bounded list of patient records matching optional search and filters."""
        clamped_limit, clamped_offset = self._sanitize_pagination(limit, offset)
        stmt = select(Patient)

        if is_synthetic is not None:
            stmt = stmt.where(Patient.is_synthetic == is_synthetic)
        if biological_sex is not None and biological_sex.strip():
            stmt = stmt.where(Patient.biological_sex == biological_sex.strip().lower())
        if search is not None and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(Patient.mrn_pseudonym.ilike(term))

        stmt = (
            stmt.order_by(Patient.created_at.desc())
            .limit(clamped_limit)
            .offset(clamped_offset)
        )
        return self.session.scalars(stmt).all()

    def count_patients(
        self,
        is_synthetic: bool | None = None,
        search: str | None = None,
        biological_sex: str | None = None,
    ) -> int:
        """Count total patient records matching criteria."""
        stmt = select(func.count(Patient.id))
        if is_synthetic is not None:
            stmt = stmt.where(Patient.is_synthetic == is_synthetic)
        if biological_sex is not None and biological_sex.strip():
            stmt = stmt.where(Patient.biological_sex == biological_sex.strip().lower())
        if search is not None and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(Patient.mrn_pseudonym.ilike(term))
        return self.session.scalar(stmt) or 0

