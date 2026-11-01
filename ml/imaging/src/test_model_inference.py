"""Smoke test for the pretrained chest X-ray research model."""

from pathlib import Path

import numpy as np
import torch
import torchxrayvision as xrv
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[3]
IMAGE_PATH = (
    PROJECT_ROOT
    / "ml"
    / "imaging"
    / "data"
    / "images"
    / "00001075_000.png"
)

def main() -> None:
    if not IMAGE_PATH.is_file():
        raise FileNotFoundError(f"Test X-ray not found: {IMAGE_PATH}")

    print("Loading pretrained DenseNet-121 model...")
    model = xrv.models.DenseNet(weights="densenet121-res224-nih")
    model.eval()

    print(f"Loading image: {IMAGE_PATH.name}")

    with Image.open(IMAGE_PATH) as image:
        image = image.convert("L")
        image_array = np.asarray(image, dtype=np.float32)

    # Normalize pixel values using TorchXRayVision preprocessing.
    image_array = xrv.datasets.normalize(image_array, 255)

    # Add the required channel dimension: (1, height, width).
    image_array = np.expand_dims(image_array, axis=0)

    # Crop and resize using TorchXRayVision transforms.
    image_array = xrv.datasets.XRayCenterCrop()(image_array)
    image_array = xrv.datasets.XRayResizer(224)(image_array)

    # Convert to a tensor: (batch, channels, height, width).
    image_tensor = torch.from_numpy(
        np.asarray(image_array, dtype=np.float32)
    ).unsqueeze(0)

    with torch.no_grad():
        output = model(image_tensor)

    scores = output.squeeze(0).cpu().numpy()
    labels = list(model.pathologies)

    if len(scores) != len(labels):
        raise RuntimeError(
            f"Output-label mismatch: {len(scores)} scores, "
            f"{len(labels)} labels."
        )

    if not np.isfinite(scores).all():
        raise RuntimeError("Model returned non-finite scores.")

    print(f"\nImage: {IMAGE_PATH.name}")
    print(f"Input tensor shape: {tuple(image_tensor.shape)}")
    print(f"Output shape: {tuple(output.shape)}")
    print("\nTop 5 model scores (not diagnostic probabilities):")

    for index in np.argsort(scores)[::-1][:5]:
        print(f"  {labels[index]}: {scores[index]:.4f}")

    print("\nSmoke test passed!")
    print("Research use only — not for clinical diagnosis.")

if __name__ == "__main__":
    main()
