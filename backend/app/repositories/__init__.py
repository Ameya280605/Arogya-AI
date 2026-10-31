"""Arogya AI — Data Access Repositories Package.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Exposes specialized SQLAlchemy repositories for clinical, research, and operational entities.
"""

from backend.app.repositories.analysis import AnalysisRepository
from backend.app.repositories.asset import AssetRepository
from backend.app.repositories.audit import AuditRepository
from backend.app.repositories.base import BaseRepository
from backend.app.repositories.dashboard import DashboardRepository
from backend.app.repositories.encounter import EncounterRepository
from backend.app.repositories.observation import ObservationRepository
from backend.app.repositories.patient import PatientRepository
from backend.app.repositories.user import RoleRepository, UserRepository

__all__ = [
    "AnalysisRepository",
    "AssetRepository",
    "AuditRepository",
    "BaseRepository",
    "DashboardRepository",
    "EncounterRepository",
    "ObservationRepository",
    "PatientRepository",
    "RoleRepository",
    "UserRepository",
]
