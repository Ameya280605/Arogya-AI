"""Clinical workspace contracts layered over the existing patient domain."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.analysis import AnalysisRunResponse
from backend.app.schemas.asset import UploadedAssetResponse
from backend.app.schemas.common import BaseSchema, ORMModel, ensure_timezone_aware
from backend.app.schemas.observation import ObservationResponse


CaseStatus = Literal["draft", "in_progress", "completed", "cancelled"]
MeasurementKind = Literal["vital", "laboratory"]
AnalysisKind = Literal["tabular", "imaging"]


class CaseMeasurement(BaseSchema):
    """A measurement captured in original units and linked to an observation."""

    kind: MeasurementKind = "vital"
    code: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    numeric_value: float | None = Field(default=None, allow_inf_nan=False)
    text_value: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=32)
    reference_low: float | None = Field(default=None, allow_inf_nan=False)
    reference_high: float | None = Field(default=None, allow_inf_nan=False)

    @field_validator("code", "display_name", "unit")
    @classmethod
    def reject_blank_strings(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("Value cannot be blank.")
        return value

    @model_validator(mode="after")
    def validate_measurement(self) -> "CaseMeasurement":
        if self.numeric_value is None and self.text_value is None:
            raise ValueError("Provide a measurement value; missing values are not zero.")
        if self.numeric_value is not None and not self.unit:
            raise ValueError("A unit is required for numeric measurements.")
        if (
            self.reference_low is not None
            and self.reference_high is not None
            and self.reference_low > self.reference_high
        ):
            raise ValueError("Reference range minimum cannot exceed its maximum.")
        return self

    def metadata(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "reference_low": self.reference_low,
            "reference_high": self.reference_high,
            "original_unit": self.unit,
        }


class ClinicalCaseFields(BaseSchema):
    encounter_type: Literal["ambulatory", "inpatient", "emergency", "synthetic"] = "ambulatory"
    status: CaseStatus = "draft"
    symptoms: str | None = Field(default=None, max_length=10000)
    symptom_duration: str | None = Field(default=None, max_length=255)
    medical_history: str | None = Field(default=None, max_length=20000)
    medications: list[str] = Field(default_factory=list, max_length=100)
    allergies: list[str] = Field(default_factory=list, max_length=100)
    clinical_notes: str | None = Field(default=None, max_length=20000)
    measurements: list[CaseMeasurement] = Field(default_factory=list, max_length=100)


class ClinicalCaseCreate(ClinicalCaseFields):
    start_time: datetime | None = None

    @field_validator("start_time")
    @classmethod
    def validate_start_time(cls, value: datetime | None) -> datetime | None:
        return ensure_timezone_aware(value)


class ClinicalCaseUpdate(BaseSchema):
    encounter_type: Literal["ambulatory", "inpatient", "emergency", "synthetic"] | None = None
    status: CaseStatus | None = None
    symptoms: str | None = Field(default=None, max_length=10000)
    symptom_duration: str | None = Field(default=None, max_length=255)
    medical_history: str | None = Field(default=None, max_length=20000)
    medications: list[str] | None = Field(default=None, max_length=100)
    allergies: list[str] | None = Field(default=None, max_length=100)
    clinical_notes: str | None = Field(default=None, max_length=20000)
    measurements: list[CaseMeasurement] | None = Field(default=None, max_length=100)


class ClinicalCaseQuality(ORMModel):
    blocking_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    ready_for_analysis: bool


class ClinicalCaseResponse(ORMModel):
    id: UUID
    patient_id: UUID
    encounter_type: str
    status: str
    start_time: datetime
    end_time: datetime | None
    symptoms: str | None
    symptom_duration: str | None
    medical_history: str | None
    medications: list[str] | None
    allergies: list[str] | None
    clinical_notes: str | None
    created_at: datetime
    updated_at: datetime
    observations: list[ObservationResponse] = Field(default_factory=list)
    attachments: list[UploadedAssetResponse] = Field(default_factory=list)
    analysis_runs: list[AnalysisRunResponse] = Field(default_factory=list)
    quality: ClinicalCaseQuality


class TabularDraftInput(BaseSchema):
    age: int | None = Field(default=None, ge=1, le=120)
    gender: int | None = Field(default=None, ge=0, le=1)
    smoking: int | None = Field(default=None, ge=1, le=3)
    imaginary_min: float | None = Field(default=None, allow_inf_nan=False)
    imaginary_avg: float | None = Field(default=None, allow_inf_nan=False)
    real_min: float | None = Field(default=None, allow_inf_nan=False)
    real_avg: float | None = Field(default=None, allow_inf_nan=False)


class ClinicalCaseAnalysisRequest(BaseSchema):
    analysis_type: AnalysisKind
    submit_now: bool = False
    tabular_input: TabularDraftInput | None = None
    asset_id: UUID | None = None
    generate_heatmap: bool = False
    heatmap_label: str = "Pneumonia"

    @model_validator(mode="after")
    def require_modality_input(self) -> "ClinicalCaseAnalysisRequest":
        if self.submit_now and self.analysis_type == "tabular" and self.tabular_input is None:
            raise ValueError("Tabular analysis requires tabular_input.")
        if self.submit_now and self.analysis_type == "imaging" and self.asset_id is None:
            raise ValueError("Imaging analysis requires asset_id.")
        if self.analysis_type == "tabular" and self.asset_id is not None:
            raise ValueError("asset_id is only valid for imaging analysis.")
        if self.analysis_type == "imaging" and self.tabular_input is not None:
            raise ValueError("tabular_input is only valid for tabular analysis.")
        return self
