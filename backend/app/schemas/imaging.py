"""Request schemas for research-only chest X-ray analysis."""

from uuid import UUID

from pydantic import Field

from backend.app.schemas.common import BaseSchema


class ImagingInferenceRequest(BaseSchema):
    """Request to analyze an existing uploaded chest X-ray."""

    asset_id: UUID = Field(
        description="ID of the previously uploaded chest X-ray asset."
    )

    encounter_id: UUID | None = Field(
        default=None,
        description="Optional encounter associated with the image.",
    )

    generate_heatmap: bool = Field(
        default=False,
        description="Whether to generate a Grad-CAM visualization.",
    )

    heatmap_label: str = Field(
        default="Pneumonia",
        min_length=1,
        max_length=100,
        description="Model label to visualize when Grad-CAM is enabled.",
    )
