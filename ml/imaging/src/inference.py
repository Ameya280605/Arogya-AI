"""Chest X-ray inference pipeline for research use only."""

from pathlib import Path

import numpy as np
import torch
import torchxrayvision as xrv
from PIL import Image

class ImagingInferenceError(ValueError):
    """Raised when image inference cannot be completed."""

class ChestXrayInference:
    """Run inference using pretrained TorchXRayVision NIH weights."""

    MODEL_WEIGHTS = "densenet121-res224-nih"

    def __init__(self) -> None:
        self.device = torch.device("cpu")
        self.model = xrv.models.DenseNet(weights=self.MODEL_WEIGHTS)
        self.model.to(self.device)
        self.model.eval()

        # Only these 14 labels are trained for the NIH checkpoint.
        self.labels = list(self.model.pathologies[:14])

        if len(self.labels) != 14:
            raise RuntimeError(
                f"Expected 14 NIH labels, got {len(self.labels)}."
            )

    @staticmethod
    def preprocess(image_path: str | Path) -> torch.Tensor:
        """Validate and preprocess an image for TorchXRayVision."""

        path = Path(image_path)

        if path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise ImagingInferenceError(
                "Unsupported format. Use PNG or JPEG images."
            )

        if not path.is_file():
            raise ImagingInferenceError("Image file not found.")

        # Reject very large files before decoding.
        max_size_bytes = 20 * 1024 * 1024

        if path.stat().st_size > max_size_bytes:
            raise ImagingInferenceError(
                "Image file exceeds the 20 MB limit."
            )

        try:
            with Image.open(path) as image:
                if image.format not in {"PNG", "JPEG"}:
                    raise ImagingInferenceError(
                        "Image contents must be PNG or JPEG."
                    )

                image.load()

                if image.width < 32 or image.height < 32:
                    raise ImagingInferenceError(
                        "Image dimensions must be at least 32x32."
                    )

                if image.width * image.height > 40_000_000:
                    raise ImagingInferenceError(
                        "Image dimensions exceed the pixel limit."
                    )

                image = image.convert("L")
                image_array = np.asarray(image, dtype=np.float32)

        except ImagingInferenceError:
            raise
        except (OSError, ValueError) as exc:
            raise ImagingInferenceError(
                "Image is corrupt or cannot be decoded."
            ) from exc

        # TorchXRayVision preprocessing: grayscale, normalize,
        # add channel dimension, center-crop, then resize to 224.
        image_array = xrv.datasets.normalize(image_array, 255)
        image_array = np.expand_dims(image_array, axis=0)
        image_array = xrv.datasets.XRayCenterCrop()(image_array)
        image_array = xrv.datasets.XRayResizer(224)(image_array)

        tensor = torch.from_numpy(
            np.asarray(image_array, dtype=np.float32)
        ).unsqueeze(0)

        if not torch.isfinite(tensor).all():
            raise ImagingInferenceError(
                "Preprocessed image contains invalid values."
            )

        return tensor

    def predict(self, image_path: str | Path) -> dict:
        """Return model scores for the 14 NIH-trained labels."""

        image_tensor = self.preprocess(image_path).to(self.device)

        try:
            with torch.inference_mode():
                output = self.model(image_tensor)

        except Exception as exc:
            raise RuntimeError("Chest X-ray model inference failed.") from exc

        if output.ndim != 2 or output.shape[0] != 1:
            raise RuntimeError(
                f"Unexpected model output shape: {tuple(output.shape)}"
            )

        if output.shape[1] < len(self.labels):
            raise RuntimeError(
                "Model returned fewer outputs than expected."
            )

        # Ignore output positions not trained for the NIH checkpoint.
        scores = output[0, :len(self.labels)].cpu().numpy()

        if not np.isfinite(scores).all():
            raise RuntimeError("Model returned non-finite scores.")

        return {
            "image_name": Path(image_path).name,
            "model": self.MODEL_WEIGHTS,
            "model_version": getattr(xrv, "__version__", "unknown"),
            "research_only": True,
            "output_type": "raw_model_scores_not_calibrated_probabilities",
            "predictions": [
                {
                    "label": label,
                    "score": float(score),
                }
                for label, score in zip(self.labels, scores)
            ],
        }

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print(
            "Usage: python -m ml.imaging.src.inference <path-to-xray>"
        )
        raise SystemExit(2)

    pipeline = ChestXrayInference()
    result = pipeline.predict(sys.argv[1])
    print(json.dumps(result, indent=2))
    print("\nResearch use only. Not for clinical diagnosis.")
