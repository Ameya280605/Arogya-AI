"""Arogya AI - API Request/Response Schemas & Data Contracts Package.

Module 3, Phase 3.4: Pydantic Request/Response Schemas & Data Contracts.
Provides decoupled, validated Pydantic data contracts for API boundaries.
"""

from backend.app.schemas.analysis import (
    AnalysisRunCreate,
    AnalysisRunResponse,
    TabularInferenceRequest,
)
from backend.app.schemas.asset import (
    AssetMetadataBase,
    AssetMetadataCreate,
    AssetMetadataResponse,
)
from backend.app.schemas.audit import (
    AuditEventFilter,
    AuditEventResponse,
)
from backend.app.schemas.common import (
    BaseSchema,
    ORMModel,
    PaginatedResponse,
    ensure_timezone_aware,
)
from backend.app.schemas.dashboard import (
    AnalysisRunStatus,
    AnalysisStatusBreakdown,
    AnalysisSummary,
    DashboardOverviewResponse,
    EncounterSummary,
    PatientSummary,
    PendingReviewItem,
    PendingReviewQueuePaginated,
    PendingReviewQueueSummary,
    RecentActivityItem,
    RecentActivitySummary,
)
from backend.app.schemas.encounter import (
    EncounterBase,
    EncounterCreate,
    EncounterResponse,
    EncounterStatus,
    EncounterType,
    EncounterUpdate,
)
from backend.app.schemas.observation import (
    ObservationBase,
    ObservationCreate,
    ObservationResponse,
)
from backend.app.schemas.patient import (
    BiologicalSex,
    PatientBase,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)
from backend.app.schemas.user import (
    RoleBase,
    RoleCreate,
    RoleResponse,
    UserBase,
    UserCreate,
    UserResponse,
    UserUpdate,
)

__all__ = [
    # Common
    "BaseSchema",
    "ORMModel",
    "PaginatedResponse",
    "ensure_timezone_aware",
    # User & Role
    "RoleBase",
    "RoleCreate",
    "RoleResponse",
    "UserBase",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    # Patient
    "BiologicalSex",
    "PatientBase",
    "PatientCreate",
    "PatientResponse",
    "PatientUpdate",
    # Encounter
    "EncounterBase",
    "EncounterCreate",
    "EncounterResponse",
    "EncounterStatus",
    "EncounterType",
    "EncounterUpdate",
    # Observation
    "ObservationBase",
    "ObservationCreate",
    "ObservationResponse",
    # Asset
    "AssetMetadataBase",
    "AssetMetadataCreate",
    "AssetMetadataResponse",
    # Analysis
    "AnalysisRunCreate",
    "AnalysisRunResponse",
    # Audit
    "AuditEventFilter",
    "AuditEventResponse",
    # Dashboard (Module 5)
    "AnalysisRunStatus",
    "AnalysisStatusBreakdown",
    "AnalysisSummary",
    "DashboardOverviewResponse",
    "EncounterSummary",
    "PatientSummary",
    "PendingReviewItem",
    "PendingReviewQueuePaginated",
    "PendingReviewQueueSummary",
    "RecentActivityItem",
    "RecentActivitySummary",
]
