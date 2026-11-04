"""Research-only chest X-ray inference and analysis lifecycle."""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.schemas.analysis import AnalysisRunCreate
from backend.app.services.clinical import ClinicalService
from backend.app.services.storage import StorageService
from backend.app.settings import get_settings
from ml.imaging.src.gradcam import ChestXrayGradCAM
from ml.imaging.src.inference import ChestXrayInference

logger = logging.getLogger("arogya.services.imaging")


class ImagingMLService:
    """Run chest X-ray inference and persist analysis results."""

    MODEL_NAME = "cxr_densenet121_nih"
    MODEL_VERSION = "densenet121-res224-nih"

    _model_lock = Lock()
    _inference_lock = Lock()
    _inference: ChestXrayInference | None = None
    _gradcam: ChestXrayGradCAM | None = None

    def __init__(self, session: Session | None = None) -> None:
        self.session = session

    @classmethod
    def _get_inference(cls) -> ChestXrayInference:
        """Load the model once and reuse it."""
        with cls._model_lock:
            if cls._inference is None:
                cls._inference = ChestXrayInference()
            return cls._inference

    @classmethod
    def _get_gradcam(
        cls,
        inference: ChestXrayInference,
    ) -> ChestXrayGradCAM:
        """Reuse the inference model for Grad-CAM."""
        with cls._model_lock:
            if cls._gradcam is None:
                cls._gradcam = ChestXrayGradCAM(inference=inference)
            return cls._gradcam

    def analyze(
        self,
        image_path: str | Path,
        *,
        generate_heatmap: bool = False,
        heatmap_path: str | Path | None = None,
        heatmap_label: str = "Pneumonia",
    ) -> dict[str, Any]:
        """Generate raw model scores and optionally a Grad-CAM heatmap."""

        inference = self._get_inference()

        # Serialize inference and Grad-CAM operations on the shared model.
        with self._inference_lock:
            result = inference.predict(image_path)

            response: dict[str, Any] = {
                **result,
                "model_name": self.MODEL_NAME,
                "model_version": self.MODEL_VERSION,
                "research_only": True,
                "disclaimer": (
                    "Research use only. Model scores are not calibrated "
                    "probabilities and must not be used as a diagnosis "
                    "or to guide treatment."
                ),
            }

            if generate_heatmap:
                if heatmap_path is None:
                    raise ValueError(
                        "heatmap_path is required when heatmap generation "
                        "is enabled."
                    )

                # Reject invalid labels rather than silently visualizing
                # a different finding.
                if heatmap_label not in inference.labels:
                    raise ValueError(
                        f"Unsupported heatmap label: {heatmap_label}"
                    )

                gradcam = self._get_gradcam(inference)
                heatmap = gradcam.generate(
                    image_path,
                    label=heatmap_label,
                    output_path=heatmap_path,
                )

                # Never expose the server's filesystem path.
                response["gradcam"] = {
                    "label": heatmap["label"],
                    "raw_model_score": heatmap["raw_model_score"],
                    "research_only": True,
                    "note": heatmap["note"],
                }

        return response

    def execute_patient_imaging_analysis(
        self,
        *,
        patient_id: UUID,
        asset_id: UUID,
        encounter_id: UUID | None = None,
        generate_heatmap: bool = False,
        heatmap_label: str = "Pneumonia",
        actor_id: UUID | None = None,
        run_id: UUID | None = None,
        before_inference: Callable[[], None] | None = None,
    ):
        """Validate an uploaded image, execute inference, and persist its run."""

        if self.session is None:
            raise RuntimeError(
                "A database session is required for persisted imaging analysis."
            )

        clinical = ClinicalService(self.session)

        # Verify that the uploaded asset exists and belongs to this patient.
        asset = clinical.get_asset(asset_id)

        if asset is None:
            raise ValueError("Uploaded imaging asset was not found.")

        if asset.patient_id != patient_id:
            raise ValueError(
                "The uploaded asset does not belong to this patient."
            )

        # This model currently supports PNG/JPEG only, not PDF or DICOM.
        if asset.media_type not in {"image/png", "image/jpeg"}:
            raise ValueError(
                "Chest X-ray inference supports PNG and JPEG images only."
            )

        if Path(asset.original_filename).suffix.lower() not in {
            ".png", ".jpg", ".jpeg"
        }:
            raise ValueError("The uploaded asset must be a PNG or JPEG image.")

        effective_encounter_id = encounter_id or asset.encounter_id

        # ClinicalService also validates patient/encounter consistency.
        if run_id is None:
            run = clinical.create_analysis_run(
                AnalysisRunCreate(
                    patient_id=patient_id,
                    encounter_id=effective_encounter_id,
                    asset_id=asset.id,
                    model_name=self.MODEL_NAME,
                    model_version=self.MODEL_VERSION,
                    parameters={
                        "generate_heatmap": generate_heatmap,
                        "heatmap_label": heatmap_label,
                        "research_only": True,
                    },
                ),
                actor_id=actor_id,
            )
        else:
            run = clinical.get_analysis_run(run_id)
            if (
                run is None
                or run.patient_id != patient_id
                or run.encounter_id != effective_encounter_id
                or run.asset_id != asset.id
                or run.model_name != self.MODEL_NAME
                or run.status not in {"draft", "queued"}
            ):
                raise ValueError("The saved analysis run is not eligible for imaging execution.")
            if run.status == "draft":
                clinical.update_analysis_status(
                    run.id,
                    status="queued",
                    actor_id=actor_id,
                )

        run.retry_payload = {
            "asset_id": str(asset.id),
            "encounter_id": str(effective_encounter_id) if effective_encounter_id else None,
            "generate_heatmap": generate_heatmap,
            "heatmap_label": heatmap_label,
        }

        now = datetime.now(timezone.utc)

        clinical.update_analysis_status(
            run.id,
            status="running",
            started_at=now,
            actor_id=actor_id,
        )
        if before_inference is not None:
            before_inference()

        try:
            settings = get_settings()
            image_path = StorageService.resolve_file_path(
                asset.storage_path,
                settings.upload_storage_dir,
            )

            heatmap_path: Path | None = None

            if generate_heatmap:
                # Store generated artifacts separately from uploaded assets.
                storage_root = Path(settings.upload_storage_dir).resolve()
                artifact_dir = storage_root.parent / "imaging_artifacts"
                StorageService.ensure_private_directory(artifact_dir)

                heatmap_path = artifact_dir / f"{run.id.hex}.png"

            results = self.analyze(
                image_path,
                generate_heatmap=generate_heatmap,
                heatmap_path=heatmap_path,
                heatmap_label=heatmap_label,
            )

            completed_run = clinical.update_analysis_status(
                run.id,
                status="completed",
                results_summary=results,
                completed_at=datetime.now(timezone.utc),
                actor_id=actor_id,
            )
            if generate_heatmap:
                completed_run.output_references = [
                    {
                        "type": "imaging_heatmap",
                        "href": f"/analysis-runs/{run.id}/imaging/heatmap",
                    }
                ]

        except Exception:
            logger.exception(
                "Imaging analysis failed for run %s", run.id
            )

            # Do not expose internal paths, model errors, or stack traces
            # through the persisted API response.
            clinical.update_analysis_status(
                run.id,
                status="failed",
                error_message="Imaging analysis failed. Check server logs.",
                completed_at=datetime.now(timezone.utc),
                actor_id=actor_id,
            )

            # The caller owns the transaction and commits the failed run.
            return run

        return run
