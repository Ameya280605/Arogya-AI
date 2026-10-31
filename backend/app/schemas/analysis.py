"""Arogya AI - Analysis Run API Schemas.

Module 3, Phase 3.4: Pydantic Request/Response Schemas & Data Contracts.
Defines contracts for requesting and inspecting AI/ML research analysis runs.
Boundary Principles:
- AnalysisRunCreate accepts run initiation requests only; clients cannot inject trusted results.
- Model execution outputs represent research signals and are segregated from ground-truth clinical data.
- Inference execution, scoring, and multi-agent workflows are implemented in subsequent modules.
"""

from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import Field
from backend.app.schemas.common import BaseSchema, ORMModel


class AnalysisRunCreate(BaseSchema):
    """Request contract for submitting a research analysis task.

    Security & Safety Notice:
    - Clients specify target data references and parameters.
    - Status, results_summary, and completion timestamps are set exclusively by internal inference workers.
    """

    patient_id: UUID = Field(
        description="Target patient identifier",
    )
    encounter_id: UUID | None = Field(
        default=None,
        description="Optional encounter context identifier",
    )
    asset_id: UUID | None = Field(
        default=None,
        description="Optional uploaded asset identifier (e.g. imaging scan to analyze)",
    )
    model_name: str = Field(
        min_length=1,
        max_length=128,
        description="Canonical model identifier (e.g. 'cxr_densenet121_baseline', 'tabular_xgb_risk')",
        examples=["cxr_densenet121_baseline"],
    )
    model_version: str = Field(
        min_length=1,
        max_length=32,
        description="Requested model release or weights version tag",
        examples=["0.1.0-alpha"],
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Optional execution hyperparameters or decision threshold overrides",
        examples=[{"confidence_threshold": 0.5}],
    )


class AnalysisRunResponse(ORMModel):
    """Response contract representing an analysis run and its evaluation output."""

    id: UUID = Field(
        description="Unique analysis run identifier",
    )
    patient_id: UUID = Field(
        description="Target patient identifier",
    )
    encounter_id: UUID | None = Field(
        default=None,
        description="Associated encounter identifier",
    )
    asset_id: UUID | None = Field(
        default=None,
        description="Evaluated asset identifier",
    )
    model_name: str = Field(
        description="Executed model identifier",
    )
    model_version: str = Field(
        description="Executed model release version",
    )
    status: str = Field(
        description="Execution lifecycle state ('queued', 'running', 'completed', 'failed', 'abstained')",
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Runtime hyperparameters applied to execution",
    )
    results_summary: dict[str, Any] | None = Field(
        default=None,
        description="Structured evaluation output (predictions, uncertainty metrics, abstention reasons)",
    )
    error_message: str | None = Field(
        default=None,
        description="Diagnostic explanation in case of failure or model abstention",
    )
    started_at: datetime | None = Field(
        default=None,
        description="Execution start timestamp in UTC",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Execution completion timestamp in UTC",
    )
    created_at: datetime = Field(
        description="Task creation timestamp in UTC",
    )


class TabularInferenceRequest(BaseSchema):
    """Request payload for evaluating tabular respiratory risk model."""

    age: int = Field(
        ge=1,
        le=120,
        description="Patient age in years (1-120)",
        examples=[65],
    )
    gender: int = Field(
        ge=0,
        le=1,
        description="Biological sex: 0=Female, 1=Male",
        examples=[1],
    )
    smoking: int = Field(
        ge=1,
        le=3,
        description="Smoking history: 1=Non-smoker, 2=Ex-smoker, 3=Active-smoker",
        examples=[2],
    )
    imaginary_min: float | None = Field(
        default=None,
        description="Optional saliva imaginary permittivity minimum",
        examples=[-320.61],
    )
    imaginary_avg: float | None = Field(
        default=None,
        description="Optional saliva imaginary permittivity average",
        examples=[-300.56],
    )
    real_min: float | None = Field(
        default=None,
        description="Optional saliva real permittivity minimum",
        examples=[-495.26],
    )
    real_avg: float | None = Field(
        default=None,
        description="Optional saliva real permittivity average",
        examples=[-464.17],
    )
    encounter_id: UUID | None = Field(
        default=None,
        description="Optional associated encounter identifier",
    )
    parameters: dict[str, Any] | None = Field(
        default=None,
        description="Optional runtime execution parameters or confidence thresholds",
    )

