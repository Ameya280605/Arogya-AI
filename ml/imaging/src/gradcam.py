"""Grad-CAM visualization for chest X-ray research use only."""

from pathlib import Path
import os

import numpy as np
import torch
import torch.nn.functional as F
import torchxrayvision as xrv
from PIL import Image

from ml.imaging.src.inference import ChestXrayInference, ImagingInferenceError


class GradCAMError(ValueError):
    """Raised when Grad-CAM cannot process the requested input."""


class ChestXrayGradCAM:
    """Generate Grad-CAM visualizations using pretrained NIH weights."""

    TARGET_LAYER = "features.denseblock4.denselayer16.conv2"
    MODEL_WEIGHTS = "densenet121-res224-nih"

    def __init__(
        self,
        inference: ChestXrayInference | None = None,
    ) -> None:
        """Initialize Grad-CAM, optionally reusing an existing inference model."""
        self.inference = (
            inference if inference is not None else ChestXrayInference()
        )
        self.model = self.inference.model
        self.device = self.inference.device
        self.labels = self.inference.labels

        modules = dict(self.model.named_modules())

        if self.TARGET_LAYER not in modules:
            raise RuntimeError(
                f"Grad-CAM target layer not found: {self.TARGET_LAYER}"
            )

        self.target_layer = modules[self.TARGET_LAYER]

    def generate(
        self,
        image_path: str | Path,
        label: str,
        output_path: str | Path,
    ) -> dict:
        """Generate a heatmap overlay and save it to output_path."""

        image_path = Path(image_path)
        output_path = Path(output_path)

        if label not in self.labels:
            raise GradCAMError(
                f"Unknown label '{label}'. Available labels: {self.labels}"
            )

        if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
            raise GradCAMError("Output must be a PNG or JPEG file.")

        try:
            input_tensor = self.inference.preprocess(image_path).to(self.device)
        except ImagingInferenceError as exc:
            raise GradCAMError(str(exc)) from exc

        activations = {}
        gradients = {}

        def capture_activations(_module, _inputs, output):
            activations["value"] = output
            output.register_hook(
                lambda grad: gradients.__setitem__("value", grad)
            )

        hook = self.target_layer.register_forward_hook(capture_activations)

        try:
            self.model.zero_grad(set_to_none=True)

            # Grad-CAM requires gradients; do not use inference_mode here.
            with torch.enable_grad():
                scores = self.model(input_tensor)

                if scores.ndim != 2 or scores.shape[0] != 1:
                    raise GradCAMError(
                        f"Unexpected model output shape: {tuple(scores.shape)}"
                    )

                if scores.shape[1] < len(self.labels):
                    raise GradCAMError("Model returned too few output scores.")

                label_index = self.labels.index(label)
                scores[0, label_index].backward()

            if "value" not in activations or "value" not in gradients:
                raise GradCAMError("Could not calculate Grad-CAM gradients.")

            feature_maps = activations["value"].detach()
            grads = gradients["value"].detach()

            weights = grads.mean(dim=(2, 3), keepdim=True)
            cam = F.relu((weights * feature_maps).sum(dim=1, keepdim=True))

            cam = F.interpolate(
                cam,
                size=(224, 224),
                mode="bilinear",
                align_corners=False,
            )[0, 0]

            cam = cam.cpu().numpy()

            if not np.isfinite(cam).all():
                raise GradCAMError("Grad-CAM produced non-finite values.")

            cam_min = float(cam.min())
            cam_max = float(cam.max())

            if cam_max > cam_min:
                cam = (cam - cam_min) / (cam_max - cam_min)
            else:
                cam = np.zeros_like(cam)

            # Load original image and resize the heatmap to match it.
            with Image.open(image_path) as image:
                original = image.convert("RGB")

            heatmap = Image.fromarray(
                np.uint8(np.clip(cam, 0.0, 1.0) * 255)
            ).resize(original.size, Image.Resampling.BILINEAR)

            heatmap_array = np.asarray(heatmap, dtype=np.float32) / 255.0

            # Red intensity represents relative Grad-CAM activation.
            colored = np.zeros(
                (heatmap_array.shape[0], heatmap_array.shape[1], 3),
                dtype=np.uint8,
            )
            colored[:, :, 0] = np.uint8(255 * heatmap_array)
            colored[:, :, 1] = np.uint8(100 * heatmap_array)

            overlay = Image.blend(
                original,
                Image.fromarray(colored),
                alpha=0.4,
            )

            output_path.parent.mkdir(
                parents=True,
                exist_ok=True,
                mode=0o700,
            )
            if os.name != "nt":
                os.chmod(output_path.parent, 0o700)
            overlay.save(output_path)
            if os.name != "nt":
                os.chmod(output_path, 0o600)

            return {
                "image_name": image_path.name,
                "label": label,
                "raw_model_score": float(
                    scores[0, label_index].detach().cpu()
                ),
                "output_path": str(output_path),
                "model": self.MODEL_WEIGHTS,
                "research_only": True,
                "note": (
                    "Grad-CAM highlights regions influencing a model score. "
                    "It is not a diagnosis or proof of disease location."
                ),
            }

        finally:
            hook.remove()
            self.model.zero_grad(set_to_none=True)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Generate a research-only chest X-ray Grad-CAM overlay."
    )
    parser.add_argument("image", help="Path to a PNG or JPEG chest X-ray")
    parser.add_argument("label", help="One of the model's 14 labels")
    parser.add_argument(
        "--output",
        default="ml/imaging/artifacts/gradcam_overlay.png",
        help="Output image path",
    )
    args = parser.parse_args()

    pipeline = ChestXrayGradCAM()
    result = pipeline.generate(args.image, args.label, args.output)
    print(json.dumps(result, indent=2))
