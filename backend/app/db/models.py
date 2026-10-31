"""Arogya AI - Initial Healthcare & Clinical Domain Entity Models.

Module 3, Phase 3.3: Initial Entities & Relational Data Models.
Defines SQLAlchemy 2.x declarative entity models for User, Role, Patient,
Encounter, Observation, UploadedAsset, AnalysisRun, and AuditEvent.

Design Principles:
- Portable SQLAlchemy types (UUID, DateTime(timezone=True), JSON).
- Explicit foreign keys, indices, and deliberate deletion policies.
- Segregation of clinical observations from AI analysis outputs.
- Uploaded asset metadata tracks file references without binary DB storage.
- Audit events provide immutable traceability without leaking PHI or credentials.
"""

from datetime import date, datetime, timezone
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    JSON,
    String,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base

# ---------------------------------------------------------------------------
# User & Role Domain Entities (RBAC Foundation)
# ---------------------------------------------------------------------------

# Explicit association table for Many-to-Many User-Role relationships
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column(
        "user_id",
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "role_id",
        Uuid,
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "assigned_at",
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    ),
)


class Role(Base):
    """System role entity representing authorization access tiers."""

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique role name (e.g. 'administrator', 'clinician', 'researcher')",
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable description of role permissions",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    users: Mapped[list["User"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )


class User(Base):
    """User account entity for clinicians, researchers, and administrators."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique user login handle",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique user contact email address",
    )
    full_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Display name of user",
    )
    hashed_password: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Cryptographic password hash; plaintext passwords strictly forbidden",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Account active status flag",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    roles: Mapped[list[Role]] = relationship(
        secondary=user_roles,
        back_populates="users",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="actor",
    )


# ---------------------------------------------------------------------------
# Clinical Domain Entities (Patient, Encounter, Observation)
# ---------------------------------------------------------------------------


class Patient(Base):
    """Patient entity representing research cohorts and synthetic profiles.

    Strictly complies with the zero-PHI governance policy: uses a generated
    UUID primary key and a pseudonymous identifier; real clinical identifiers
    must never be stored in this table.
    """

    __tablename__ = "patients"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    mrn_pseudonym: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        doc="De-identified or synthetic medical record number (e.g. 'SYNTH-PAT-0001')",
    )
    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        doc="Date or synthetic birth reference for demographic stratification",
    )
    biological_sex: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        doc="Biological sex ('male', 'female', 'other', 'unknown')",
    )
    is_synthetic: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="True for artificially generated records; False for licensed research datasets",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships (Deletion policy: RESTRICT prevents accidental cascading loss of clinical history)
    encounters: Mapped[list["Encounter"]] = relationship(
        back_populates="patient",
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="patient",
    )
    uploaded_assets: Mapped[list["UploadedAsset"]] = relationship(
        back_populates="patient",
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="patient",
    )


class Encounter(Base):
    """Clinical encounter representing an interaction or study epoch for a patient."""

    __tablename__ = "encounters"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Foreign key to owning patient record",
    )
    encounter_type: Mapped[str] = mapped_column(
        String(32),
        default="ambulatory",
        nullable=False,
        index=True,
        doc="Classification ('ambulatory', 'inpatient', 'emergency', 'synthetic')",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="in_progress",
        nullable=False,
        index=True,
        doc="Encounter state ('planned', 'in_progress', 'completed', 'cancelled')",
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Commencement timestamp of encounter",
    )
    end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Conclusion timestamp of encounter",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patient: Mapped[Patient] = relationship(
        back_populates="encounters",
    )
    observations: Mapped[list["Observation"]] = relationship(
        back_populates="encounter",
    )
    uploaded_assets: Mapped[list["UploadedAsset"]] = relationship(
        back_populates="encounter",
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="encounter",
    )


class Observation(Base):
    """Structured clinical measurement or observation (vital signs, lab values).

    Represents quantitative and qualitative clinical observations distinctly
    via numeric_value and text_value. Strictly separated from AI model interpretations.
    """

    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("encounters.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Foreign key to associated encounter",
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Direct foreign key to patient for fast cohort querying",
    )
    code: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Standardized coding system or canonical name (e.g. '8867-4', 'heart_rate')",
    )
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="Human-readable concept title (e.g. 'Heart Rate')",
    )
    numeric_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        doc="Quantitative measurement value",
    )
    text_value: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Qualitative or categorical finding",
    )
    unit: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
        doc="Standard measurement unit (e.g. 'bpm', 'mg/dL', 'degC')",
    )
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        doc="Timestamp when measurement was acquired",
    )
    source_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Device/synthesizer metadata; strictly contains no diagnostic interpretation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    encounter: Mapped[Encounter] = relationship(
        back_populates="observations",
    )
    patient: Mapped[Patient] = relationship(
        back_populates="observations",
    )


# ---------------------------------------------------------------------------
# Research & Multimodal Pipeline Entities (Assets, Analysis Runs)
# ---------------------------------------------------------------------------


class UploadedAsset(Base):
    """Metadata tracking uploaded files and medical imaging attachments.

    Binary payloads are stored in local secure object volumes; this table
    tracks only metadata, storage locators, and verification checksums.
    """

    __tablename__ = "uploaded_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Foreign key to owning patient",
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("encounters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to associated encounter",
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Sanitized display filename",
    )
    media_type: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        doc="MIME media type (e.g. 'image/png', 'application/dicom')",
    )
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        doc="Size of binary payload in bytes",
    )
    storage_path: Mapped[str] = mapped_column(
        String(512),
        unique=True,
        nullable=False,
        index=True,
        doc="Opaque relative storage locator on filesystem or object store",
    )
    checksum_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="SHA-256 cryptographic digest for integrity verification",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patient: Mapped[Patient] = relationship(
        back_populates="uploaded_assets",
    )
    encounter: Mapped[Encounter | None] = relationship(
        back_populates="uploaded_assets",
    )
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="asset",
    )


class AnalysisRun(Base):
    """Record of an AI or research model analysis execution.

    Segregates model predictions, hyperparameters, and execution status
    from primary clinical observations. Outputs represent research evaluations,
    not validated medical conclusions.
    """

    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Foreign key to patient evaluated in run",
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("encounters.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to associated encounter context",
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("uploaded_assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to evaluated image or document asset",
    )
    model_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        doc="Canonical model identifier (e.g. 'cxr_densenet121_baseline', 'tabular_xgb_risk')",
    )
    model_version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        doc="Exact model release or weights version tag",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="queued",
        nullable=False,
        index=True,
        doc="Execution status ('queued', 'running', 'completed', 'failed', 'abstained')",
    )
    parameters: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Execution parameters and decision thresholds",
    )
    results_summary: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Structured model output container; strictly segregated from observations",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Diagnostic message in case of failure or abstention",
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Run commencement timestamp",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Run completion timestamp",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    patient: Mapped[Patient] = relationship(
        back_populates="analysis_runs",
    )
    encounter: Mapped[Encounter | None] = relationship(
        back_populates="analysis_runs",
    )
    asset: Mapped[UploadedAsset | None] = relationship(
        back_populates="analysis_runs",
    )


# ---------------------------------------------------------------------------
# Audit & Governance Entities (AuditEvent)
# ---------------------------------------------------------------------------


class AuditEvent(Base):
    """Immutable audit log event for system traceability.

    Preserves operational audit records even if acting users are deactivated.
    Strictly forbids storing plaintext credentials, session tokens, or PHI in metadata.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        doc="Classification of event (e.g. 'user.login', 'case.created', 'analysis.started')",
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Optional foreign key to initiating user; preserved as NULL if user deleted",
    )
    action: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Action type ('create', 'read', 'update', 'delete', 'execute')",
    )
    resource_type: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Target entity type ('patient', 'encounter', 'asset', 'analysis_run')",
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="String identifier of targeted entity",
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Human-readable event summary",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        doc="Client IP address (IPv4 or IPv6 format)",
    )
    event_metadata: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Operational tracking metadata (e.g. request_id); strictly no PHI or credentials",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        doc="Immutable event timestamp",
    )

    # Relationships
    actor: Mapped[User | None] = relationship(
        back_populates="audit_events",
    )


__all__ = [
    "AnalysisRun",
    "AuditEvent",
    "Encounter",
    "Observation",
    "Patient",
    "Role",
    "UploadedAsset",
    "User",
    "user_roles",
]
