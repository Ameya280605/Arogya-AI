"""Arogya AI — Clinical Domain Service.

Module 3, Phase 3.6: Data Access Repositories & Clinical Domain Service Layer.
Coordinates clinical patient history, encounters, observations, asset metadata,
and AI analysis runs while enforcing cross-entity referential integrity and consistency.

CONSISTENCY & INVARIANT RULES:
1. Patient Existence: Encounters, observations, assets, and analysis runs must reference existing patients.
2. Encounter-Patient Integrity: Observations must reference an encounter belonging to the same patient.
3. Asset Ownership Consistency: If an asset links to an encounter, that encounter must belong to the asset's patient.
4. Multimodal Analysis Integrity: Assets evaluated in an analysis run must belong to the encounter's patient.
5. MRN Mapping: Maps 'mrn' / 'mrn_pseudonym' transparently to the underlying persistence model.
6. Zero Clinical Diagnosis: Output containers and results reflect research evaluations, not certified medical conclusions.
7. Transaction Ownership: The caller strictly owns transaction commit/rollback boundaries. ClinicalService never commits or rolls back independently.
"""

from datetime import date, datetime, timezone
from typing import Any, Sequence
from uuid import UUID
from sqlalchemy.orm import Session

from backend.app.db.models import (
    AnalysisRun,
    Encounter,
    Observation,
    Patient,
    UploadedAsset,
)
from backend.app.repositories.analysis import AnalysisRepository
from backend.app.repositories.asset import AssetRepository
from backend.app.repositories.encounter import EncounterRepository
from backend.app.repositories.observation import ObservationRepository
from backend.app.repositories.patient import PatientRepository
from backend.app.schemas.analysis import AnalysisRunCreate
from backend.app.schemas.asset import AssetMetadataCreate
from backend.app.schemas.encounter import EncounterCreate, EncounterUpdate
from backend.app.schemas.observation import ObservationCreate
from backend.app.schemas.patient import (
    DataQualityIssue,
    DataQualityReport,
    PatientCreate,
    PatientTimelineItem,
    PatientTimelineResponse,
    PatientUpdate,
)
from backend.app.services.audit import AuditService
from backend.app.services.exceptions import (
    ConsistencyError,
    DuplicateEntityError,
    EntityNotFoundError,
)


class ClinicalService:
    """Domain service managing clinical entities and enforcing relational consistency."""

    def __init__(self, session: Session) -> None:
        """Initialize ClinicalService with active session and underlying repositories."""
        self.session = session
        self.patient_repo = PatientRepository(session)
        self.encounter_repo = EncounterRepository(session)
        self.obs_repo = ObservationRepository(session)
        self.asset_repo = AssetRepository(session)
        self.analysis_repo = AnalysisRepository(session)
        self.audit_service = AuditService(session)

    # -------------------------------------------------------------------------
    # Patient Cohort Management
    # -------------------------------------------------------------------------

    def create_patient(
        self,
        data: PatientCreate,
        actor_id: UUID | None = None,
    ) -> Patient:
        """Register a new research or synthetic patient, enforcing pseudonymous MRN uniqueness."""
        # Check uniqueness of mrn_pseudonym (supports alias 'mrn')
        if self.patient_repo.get_by_mrn(data.mrn_pseudonym) is not None:
            raise DuplicateEntityError("Patient", "mrn", data.mrn_pseudonym)

        patient = self.patient_repo.create(
            mrn_pseudonym=data.mrn_pseudonym,
            birth_date=data.birth_date,
            biological_sex=data.biological_sex,
            is_synthetic=data.is_synthetic,
        )

        self.audit_service.record_event(
            event_type="patient.created",
            action="create",
            actor_id=actor_id,
            resource_type="patient",
            resource_id=str(patient.id),
            description=f"Created patient cohort record '{patient.mrn_pseudonym}'",
            event_metadata={
                "mrn_pseudonym": patient.mrn_pseudonym,
                "is_synthetic": patient.is_synthetic,
            },
        )
        return patient

    def get_patient(self, patient_id: UUID) -> Patient | None:
        """Retrieve patient entity by primary key UUID."""
        return self.patient_repo.get_by_id(patient_id)

    def get_patient_by_mrn(self, mrn: str) -> Patient | None:
        """Retrieve patient entity by pseudonymous MRN."""
        return self.patient_repo.get_by_mrn(mrn)

    def update_patient(
        self,
        patient_id: UUID,
        data: PatientUpdate,
        actor_id: UUID | None = None,
    ) -> Patient:
        """Update mutable attributes on a patient record."""
        patient = self.patient_repo.get_by_id(patient_id)
        if patient is None:
            raise EntityNotFoundError("Patient", patient_id)

        updated_patient = self.patient_repo.update(
            patient=patient,
            birth_date=data.birth_date,
            biological_sex=data.biological_sex,
            is_synthetic=data.is_synthetic,
        )

        self.audit_service.record_event(
            event_type="patient.updated",
            action="update",
            actor_id=actor_id,
            resource_type="patient",
            resource_id=str(patient.id),
            description=f"Updated patient profile '{patient.mrn_pseudonym}'",
            event_metadata={"mrn_pseudonym": patient.mrn_pseudonym},
        )
        return updated_patient

    def list_patients(
        self,
        limit: int = 100,
        offset: int = 0,
        is_synthetic: bool | None = None,
        search: str | None = None,
        biological_sex: str | None = None,
    ) -> Sequence[Patient]:
        """Retrieve bounded list of patients matching search criteria and demographic filters."""
        return self.patient_repo.list_patients(
            limit=limit,
            offset=offset,
            is_synthetic=is_synthetic,
            search=search,
            biological_sex=biological_sex,
        )

    def count_patients(
        self,
        is_synthetic: bool | None = None,
        search: str | None = None,
        biological_sex: str | None = None,
    ) -> int:
        """Count total patients matching search and demographic criteria."""
        return self.patient_repo.count_patients(
            is_synthetic=is_synthetic,
            search=search,
            biological_sex=biological_sex,
        )


    # -------------------------------------------------------------------------
    # Encounter Management
    # -------------------------------------------------------------------------

    def create_encounter(
        self,
        data: EncounterCreate,
        actor_id: UUID | None = None,
    ) -> Encounter:
        """Create a clinical encounter, validating patient existence."""
        patient = self.patient_repo.get_by_id(data.patient_id)
        if patient is None:
            raise EntityNotFoundError("Patient", data.patient_id)

        encounter = self.encounter_repo.create(
            patient_id=data.patient_id,
            start_time=data.start_time,
            end_time=data.end_time,
            encounter_type=data.encounter_type,
            status=data.status,
        )

        self.audit_service.record_event(
            event_type="encounter.created",
            action="create",
            actor_id=actor_id,
            resource_type="encounter",
            resource_id=str(encounter.id),
            description=f"Created encounter for patient '{patient.mrn_pseudonym}'",
            event_metadata={
                "patient_id": str(encounter.patient_id),
                "encounter_type": encounter.encounter_type,
            },
        )
        return encounter

    def get_encounter(self, encounter_id: UUID) -> Encounter | None:
        """Retrieve encounter by primary key UUID."""
        return self.encounter_repo.get_by_id(encounter_id)

    def update_encounter(
        self,
        encounter_id: UUID,
        data: EncounterUpdate,
        actor_id: UUID | None = None,
    ) -> Encounter:
        """Update mutable fields on an existing encounter record."""
        encounter = self.encounter_repo.get_by_id(encounter_id)
        if encounter is None:
            raise EntityNotFoundError("Encounter", encounter_id)

        updated_encounter = self.encounter_repo.update(
            encounter=encounter,
            status=data.status,
            end_time=data.end_time,
            encounter_type=data.encounter_type,
        )

        self.audit_service.record_event(
            event_type="encounter.updated",
            action="update",
            actor_id=actor_id,
            resource_type="encounter",
            resource_id=str(encounter.id),
            description=f"Updated encounter '{encounter.id}' status to '{encounter.status}'",
            event_metadata={"status": encounter.status},
        )
        return updated_encounter

    def list_encounters_by_patient(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> Sequence[Encounter]:
        """Retrieve bounded list of encounters for a patient."""
        return self.encounter_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    # -------------------------------------------------------------------------
    # Observation Management
    # -------------------------------------------------------------------------

    def create_observation(
        self,
        data: ObservationCreate,
        actor_id: UUID | None = None,
    ) -> Observation:
        """Record a clinical observation, validating encounter existence and patient consistency.

        Raises:
            EntityNotFoundError: If the associated encounter does not exist.
            ConsistencyError: If the observation's patient_id does not match the encounter's patient_id.
        """
        # 1. Verify encounter exists
        encounter = self.encounter_repo.get_by_id(data.encounter_id)
        if encounter is None:
            raise EntityNotFoundError("Encounter", data.encounter_id)

        # 2. Enforce cross-entity ownership invariant
        if encounter.patient_id != data.patient_id:
            raise ConsistencyError(
                f"Observation patient_id '{data.patient_id}' does not match "
                f"encounter patient_id '{encounter.patient_id}'."
            )

        # 3. Create observation
        observation = self.obs_repo.create(
            encounter_id=data.encounter_id,
            patient_id=data.patient_id,
            code=data.code,
            display_name=data.display_name,
            observed_at=data.observed_at,
            numeric_value=data.numeric_value,
            text_value=data.text_value,
            unit=data.unit,
            source_metadata=data.source_metadata,
        )

        self.audit_service.record_event(
            event_type="observation.created",
            action="create",
            actor_id=actor_id,
            resource_type="observation",
            resource_id=str(observation.id),
            description=f"Recorded observation '{observation.display_name}' ({observation.code})",
            event_metadata={
                "code": observation.code,
                "encounter_id": str(observation.encounter_id),
                "patient_id": str(observation.patient_id),
            },
        )
        return observation

    def get_observation(self, observation_id: UUID) -> Observation | None:
        """Retrieve observation by primary key UUID."""
        return self.obs_repo.get_by_id(observation_id)

    def list_observations_by_encounter(
        self,
        encounter_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Observation]:
        """Retrieve bounded list of observations recorded during an encounter."""
        return self.obs_repo.list_by_encounter(
            encounter_id=encounter_id,
            limit=limit,
            offset=offset,
        )

    def list_observations_by_patient(
        self,
        patient_id: UUID,
        code: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Observation]:
        """Retrieve bounded longitudinal observations for a patient."""
        return self.obs_repo.list_by_patient(
            patient_id=patient_id,
            code=code,
            limit=limit,
            offset=offset,
        )

    # -------------------------------------------------------------------------
    # Uploaded Asset Metadata Management
    # -------------------------------------------------------------------------

    def register_asset_metadata(
        self,
        data: AssetMetadataCreate,
        storage_path: str,
        actor_id: UUID | None = None,
    ) -> UploadedAsset:
        """Register file or imaging asset metadata, enforcing cross-entity ownership.

        Args:
            data: Validated client metadata payload (patient_id, encounter_id, filename, checksum).
            storage_path: Internal opaque filesystem/object storage path assigned by the server.
            actor_id: Optional UUID of the actor performing the upload.

        Raises:
            EntityNotFoundError: If patient or encounter does not exist.
            ConsistencyError: If the encounter belongs to a different patient.
            DuplicateEntityError: If storage_path is already registered.
        """
        # 1. Verify patient exists
        patient = self.patient_repo.get_by_id(data.patient_id)
        if patient is None:
            raise EntityNotFoundError("Patient", data.patient_id)

        # 2. If encounter is specified, verify existence and patient alignment
        if data.encounter_id is not None:
            encounter = self.encounter_repo.get_by_id(data.encounter_id)
            if encounter is None:
                raise EntityNotFoundError("Encounter", data.encounter_id)
            if encounter.patient_id != data.patient_id:
                raise ConsistencyError(
                    f"Asset encounter '{data.encounter_id}' belongs to patient "
                    f"'{encounter.patient_id}', not '{data.patient_id}'."
                )

        # 3. Verify unique storage path
        if self.asset_repo.get_by_storage_path(storage_path) is not None:
            raise DuplicateEntityError("UploadedAsset", "storage_path", storage_path)

        asset = self.asset_repo.create(
            patient_id=data.patient_id,
            encounter_id=data.encounter_id,
            original_filename=data.original_filename,
            media_type=data.media_type,
            file_size_bytes=data.file_size_bytes,
            storage_path=storage_path,
            checksum_sha256=data.checksum_sha256,
        )

        self.audit_service.record_event(
            event_type="asset.registered",
            action="create",
            actor_id=actor_id,
            resource_type="asset",
            resource_id=str(asset.id),
            description=f"Registered asset metadata '{asset.original_filename}'",
            event_metadata={
                "filename": asset.original_filename,
                "media_type": asset.media_type,
                "patient_id": str(asset.patient_id),
                "checksum_sha256": asset.checksum_sha256,
            },
        )
        return asset

    def get_asset(self, asset_id: UUID) -> UploadedAsset | None:
        """Retrieve uploaded asset metadata by primary key UUID."""
        return self.asset_repo.get_by_id(asset_id)

    def list_assets_by_patient(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[UploadedAsset]:
        """Retrieve bounded list of asset metadata records for a patient."""
        return self.asset_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
        )

    # -------------------------------------------------------------------------
    # Analysis Run Management
    # -------------------------------------------------------------------------

    def create_analysis_run(
        self,
        data: AnalysisRunCreate,
        actor_id: UUID | None = None,
    ) -> AnalysisRun:
        """Create a new AI analysis execution run, validating cross-entity associations.

        Raises:
            EntityNotFoundError: If encounter or asset does not exist.
            ConsistencyError: If the asset does not match the encounter's patient.
        """
        # 1. Verify patient exists
        patient = self.patient_repo.get_by_id(data.patient_id)
        if patient is None:
            raise EntityNotFoundError("Patient", data.patient_id)

        # 2. If encounter is specified, verify existence and patient alignment
        if data.encounter_id is not None:
            encounter = self.encounter_repo.get_by_id(data.encounter_id)
            if encounter is None:
                raise EntityNotFoundError("Encounter", data.encounter_id)
            if encounter.patient_id != data.patient_id:
                raise ConsistencyError(
                    f"Analysis encounter '{data.encounter_id}' belongs to patient "
                    f"'{encounter.patient_id}', not '{data.patient_id}'."
                )

        # 3. If asset is specified, verify existence and patient consistency
        if data.asset_id is not None:
            asset = self.asset_repo.get_by_id(data.asset_id)
            if asset is None:
                raise EntityNotFoundError("UploadedAsset", data.asset_id)
            if asset.patient_id != data.patient_id:
                raise ConsistencyError(
                    f"Asset patient '{asset.patient_id}' does not match "
                    f"analysis patient '{data.patient_id}'."
                )
            if data.encounter_id is not None and asset.encounter_id is not None and asset.encounter_id != data.encounter_id:
                raise ConsistencyError(
                    f"Asset encounter '{asset.encounter_id}' does not match "
                    f"analysis encounter '{data.encounter_id}'."
                )

        # 4. Create analysis run with initial 'queued' status
        run = self.analysis_repo.create(
            patient_id=data.patient_id,
            encounter_id=data.encounter_id,
            asset_id=data.asset_id,
            model_name=data.model_name,
            model_version=data.model_version,
            status="queued",
            parameters=data.parameters,
        )

        self.audit_service.record_event(
            event_type="analysis.queued",
            action="create",
            actor_id=actor_id,
            resource_type="analysis_run",
            resource_id=str(run.id),
            description=f"Queued analysis run '{run.model_name}' ({run.model_version})",
            event_metadata={
                "model_name": run.model_name,
                "model_version": run.model_version,
                "encounter_id": str(run.encounter_id),
                "patient_id": str(run.patient_id),
            },
        )
        return run

    def update_analysis_status(
        self,
        run_id: UUID,
        status: str,
        results_summary: dict[str, Any] | None = None,
        error_message: str | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        actor_id: UUID | None = None,
    ) -> AnalysisRun:
        """Update analysis run execution lifecycle status and evaluation containers."""
        run = self.analysis_repo.get_by_id(run_id)
        if run is None:
            raise EntityNotFoundError("AnalysisRun", run_id)

        updated_run = self.analysis_repo.update_status(
            run=run,
            status=status,
            results_summary=results_summary,
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
        )

        self.audit_service.record_event(
            event_type="analysis.status_updated",
            action="update",
            actor_id=actor_id,
            resource_type="analysis_run",
            resource_id=str(run.id),
            description=f"Updated analysis run '{run.id}' status to '{run.status}'",
            event_metadata={"status": run.status},
        )
        return updated_run

    def get_analysis_run(self, run_id: UUID) -> AnalysisRun | None:
        """Retrieve analysis run by primary key UUID."""
        return self.analysis_repo.get_by_id(run_id)

    def list_analysis_runs_by_patient(
        self,
        patient_id: UUID,
        limit: int = 100,
        offset: int = 0,
        status: str | None = None,
    ) -> Sequence[AnalysisRun]:
        """Retrieve bounded list of analysis runs associated with a patient."""
        return self.analysis_repo.list_by_patient(
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            status=status,
        )

    def count_encounters_by_patient(
        self,
        patient_id: UUID,
        status: str | None = None,
    ) -> int:
        """Count total encounter records for a patient."""
        return self.encounter_repo.count_by_patient(patient_id=patient_id, status=status)

    def count_observations_by_encounter(
        self,
        encounter_id: UUID,
    ) -> int:
        """Count total observations recorded during an encounter."""
        return self.obs_repo.count_by_encounter(encounter_id=encounter_id)

    def count_observations_by_patient(
        self,
        patient_id: UUID,
        code: str | None = None,
    ) -> int:
        """Count total observations recorded for a patient."""
        return self.obs_repo.count_by_patient(patient_id=patient_id, code=code)

    def count_analysis_runs_by_patient(
        self,
        patient_id: UUID,
        status: str | None = None,
    ) -> int:
        """Count total analysis runs for a patient."""
        return self.analysis_repo.count_by_patient(patient_id=patient_id, status=status)

    # -------------------------------------------------------------------------
    # Data Quality & Longitudinal Intelligence
    # -------------------------------------------------------------------------

    def evaluate_data_quality(self, patient_id: UUID) -> DataQualityReport:
        """Evaluate demographic completeness, clinical density, and measurement unit integrity.

        Analyzes:
        - Demographic completeness (MRN, birth date, biological sex).
        - Clinical continuity (encounters and observations counts).
        - Unit specification and physiological bounds for vital signs.
        - Temporal sanity (birth date, observation timestamps, encounter bounds).

        Raises:
            EntityNotFoundError: If the patient record does not exist.
        """
        patient = self.patient_repo.get_by_id(patient_id)
        if patient is None:
            raise EntityNotFoundError("Patient", patient_id)

        encounters = self.encounter_repo.list_by_patient(patient_id=patient_id, limit=200)
        observations = self.obs_repo.list_by_patient(patient_id=patient_id, limit=500)

        issues: list[DataQualityIssue] = []
        demographic_score = 0
        clinical_score = 0

        # 1. Demographic Quality Evaluation (Max 100)
        if patient.mrn_pseudonym:
            demographic_score += 30

        if patient.birth_date is not None:
            demographic_score += 40
            if patient.birth_date > date.today():
                issues.append(
                    DataQualityIssue(
                        category="temporal",
                        severity="critical",
                        field="birth_date",
                        message="Recorded birth date is in the future.",
                    )
                )
        else:
            issues.append(
                DataQualityIssue(
                    category="demographic",
                    severity="warning",
                    field="birth_date",
                    message="Birth date is missing. Age-stratified analysis and baselines cannot be computed.",
                )
            )

        if patient.biological_sex and patient.biological_sex.lower() not in ("unknown", ""):
            demographic_score += 30
        else:
            issues.append(
                DataQualityIssue(
                    category="demographic",
                    severity="info",
                    field="biological_sex",
                    message="Biological sex classification is unspecified or unknown. Normal reference ranges cannot be sex-stratified.",
                )
            )

        # 2. Clinical History Evaluation (Max 100)
        if len(encounters) > 0:
            clinical_score += 40
            for enc in encounters:
                if enc.end_time and enc.end_time < enc.start_time:
                    issues.append(
                        DataQualityIssue(
                            category="temporal",
                            severity="warning",
                            field="encounter.end_time",
                            message=f"Encounter '{enc.id}' end time precedes its commencement time.",
                        )
                    )
        else:
            issues.append(
                DataQualityIssue(
                    category="clinical",
                    severity="info",
                    field="encounters",
                    message="No clinical encounters have been recorded for this patient profile.",
                )
            )

        if len(observations) >= 3:
            clinical_score += 60
        elif len(observations) > 0:
            clinical_score += 35
        else:
            issues.append(
                DataQualityIssue(
                    category="clinical",
                    severity="info",
                    field="observations",
                    message="No physiological measurements or vital signs recorded.",
                )
            )

        # 3. Measurement Unit & Physiological Bounds Checks
        now_utc = datetime.now(timezone.utc)
        for obs in observations:
            obs_dt = obs.observed_at
            if obs_dt.tzinfo is None:
                obs_dt = obs_dt.replace(tzinfo=timezone.utc)
            if obs_dt > now_utc:
                issues.append(
                    DataQualityIssue(
                        category="temporal",
                        severity="warning",
                        field=f"obs:{obs.code}",
                        message=f"Observation '{obs.display_name}' ({obs.code}) has an acquisition timestamp in the future.",
                    )
                )

            # Missing standard unit check for numeric measurements
            if obs.numeric_value is not None and not obs.unit:
                issues.append(
                    DataQualityIssue(
                        category="unit",
                        severity="warning",
                        field=f"obs:{obs.code}",
                        message=f"Numeric observation '{obs.display_name}' ({obs.numeric_value}) lacks a standard measurement unit.",
                    )
                )

            val = obs.numeric_value
            code_lower = (obs.code or "").lower()
            name_lower = (obs.display_name or "").lower()
            if val is not None:
                # Heart Rate: standard plausible range 30-220 bpm
                if "heart" in name_lower or "pulse" in name_lower or "8867-4" in code_lower:
                    if val < 30 or val > 220:
                        issues.append(
                            DataQualityIssue(
                                category="clinical",
                                severity="warning",
                                field=f"obs:{obs.code}",
                                message=f"Heart rate value {val} {obs.unit or 'bpm'} is outside plausible physiological bounds (30-220 bpm).",
                            )
                        )
                # Body Temperature: standard plausible range 32-43 °C
                elif "temp" in name_lower or "8310-5" in code_lower:
                    if val < 32.0 or val > 43.0:
                        issues.append(
                            DataQualityIssue(
                                category="clinical",
                                severity="warning",
                                field=f"obs:{obs.code}",
                                message=f"Body temperature {val} {obs.unit or '°C'} is outside plausible physiological bounds (32.0-43.0 °C).",
                            )
                        )
                # Respiratory Rate: standard plausible range 6-60 breaths/min
                elif "respirat" in name_lower or "9279-1" in code_lower:
                    if val < 6 or val > 60:
                        issues.append(
                            DataQualityIssue(
                                category="clinical",
                                severity="warning",
                                field=f"obs:{obs.code}",
                                message=f"Respiratory rate {val} breaths/min is outside standard physiological bounds (6-60).",
                            )
                        )
                # Oxygen Saturation (SpO2): plausible range 50-100%
                elif "spo2" in name_lower or "oxygen" in name_lower or "2708-6" in code_lower:
                    if val < 50 or val > 100:
                        issues.append(
                            DataQualityIssue(
                                category="clinical",
                                severity="warning",
                                field=f"obs:{obs.code}",
                                message=f"Oxygen saturation {val}% is outside plausible bounds (50-100%).",
                            )
                        )

        completeness_score = int(demographic_score * 0.4 + clinical_score * 0.6)
        has_warnings = any(i.severity in ("warning", "critical") for i in issues)

        return DataQualityReport(
            patient_id=patient_id,
            completeness_score=completeness_score,
            demographic_score=demographic_score,
            clinical_score=clinical_score,
            issues=issues,
            has_warnings=has_warnings,
        )

    def get_patient_timeline(
        self,
        patient_id: UUID,
        limit: int = 50,
    ) -> PatientTimelineResponse:
        """Construct a unified, chronological timeline across all encounters, observations, and analyses."""
        patient = self.patient_repo.get_by_id(patient_id)
        if patient is None:
            raise EntityNotFoundError("Patient", patient_id)

        items: list[PatientTimelineItem] = []

        # 1. Encounters
        encounters = self.encounter_repo.list_by_patient(patient_id=patient_id, limit=limit)
        for enc in encounters:
            ts = enc.start_time
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            items.append(
                PatientTimelineItem(
                    id=str(enc.id),
                    event_type="encounter",
                    title=f"{enc.encounter_type.capitalize()} Encounter",
                    description=f"Status: {enc.status}. Started: {ts.strftime('%Y-%m-%d %H:%M UTC')}",
                    timestamp=ts,
                    status=enc.status,
                    metadata={
                        "encounter_type": enc.encounter_type,
                        "end_time": enc.end_time.isoformat() if enc.end_time else None,
                    },
                )
            )

        # 2. Observations
        observations = self.obs_repo.list_by_patient(patient_id=patient_id, limit=limit)
        for obs in observations:
            val_str = (
                f"{obs.numeric_value} {obs.unit or ''}".strip()
                if obs.numeric_value is not None
                else (obs.text_value or "")
            )
            ts = obs.observed_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            items.append(
                PatientTimelineItem(
                    id=str(obs.id),
                    event_type="observation",
                    title=f"Observation: {obs.display_name}",
                    description=f"Recorded: {val_str} (LOINC: {obs.code})",
                    timestamp=ts,
                    status="recorded",
                    metadata={
                        "code": obs.code,
                        "value": val_str,
                        "encounter_id": str(obs.encounter_id),
                    },
                )
            )

        # 3. Analysis Runs
        runs = self.analysis_repo.list_by_patient(patient_id=patient_id, limit=limit)
        for run in runs:
            ts = run.completed_at or run.started_at or run.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            items.append(
                PatientTimelineItem(
                    id=str(run.id),
                    event_type="analysis_run",
                    title=f"Analysis: {run.model_name}",
                    description=f"Version: {run.model_version} | Status: {run.status}",
                    timestamp=ts,
                    status=run.status,
                    metadata={
                        "model_name": run.model_name,
                        "model_version": run.model_version,
                        "results_summary": run.results_summary,
                    },
                )
            )

        # Sort descending (most recent first)
        items.sort(key=lambda x: x.timestamp, reverse=True)
        bounded_items = items[:limit]

        return PatientTimelineResponse(
            patient_id=patient_id,
            items=bounded_items,
            total=len(items),
        )

