"""Arogya AI — Domain Services Package.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Exposes coordinated domain services, cross-entity consistency validators,
operational audit logging, and domain exception classes.
"""

from backend.app.services.audit import AuditService
from backend.app.services.clinical import ClinicalService
from backend.app.services.dashboard import DashboardService
from backend.app.services.exceptions import (
    ConsistencyError,
    DomainError,
    DomainValidationError,
    DuplicateEntityError,
    EntityNotFoundError,
)
from backend.app.services.user import UserService

__all__ = [
    "AuditService",
    "ClinicalService",
    "ConsistencyError",
    "DashboardService",
    "DomainError",
    "DomainValidationError",
    "DuplicateEntityError",
    "EntityNotFoundError",
    "UserService",
]
