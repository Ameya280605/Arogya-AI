"""Image validation and preprocessing for the Arogya AI research pipeline."""

from pathlib import Path

import torch
from PIL import Image, ImageFile
from torchvision import transforms

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg"}
DEFAULT_IMAGE_SIZE = 224

# Avoid silently accepting truncated images.
ImageFile.LOAD_TRUNCATED_IMAGES = False


class ImagePreprocessingError(ValueError):
    """Raised when an image cannot be safely preprocessed."""


def preprocess_image(
    image_path: str | Path,
    image_size: int = DEFAULT_IMAGE_SIZE,
) -> torch.Tensor:
    """Validate and preprocess a chest X-ray for model inference.

    Returns:
        Tensor with shape (1, 3, image_size, image_size).

    Raises:
        ImagePreprocessingError: If the input is invalid or unreadable.
    """
    path = Path(image_path)

    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ImagePreprocessingError(
            f"Unsupported image format: {path.suffix or '(no extension)'}. "
            f"Supported formats: {', '.join(sorted(SUPPORTED_FORMATS))}"
        )

    if not path.is_file():
        raise ImagePreprocessingError(f"Image file not found: {path}")

    if image_size <= 0:
        raise ImagePreprocessingError("image_size must be greater than zero.")

    try:
        with Image.open(path) as image:
            if image.format not in {"PNG", "JPEG"}:
                raise ImagePreprocessingError(
                    f"Unsupported image content: {image.format}"
                )

            image.load()

            if image.width < 32 or image.height < 32:
                raise ImagePreprocessingError(
                    f"Image dimensions are too small: {image.size}"
                )

            image = image.convert("RGB")

            transform = transforms.Compose(
                [
                    transforms.Resize((image_size, image_size)),
                    transforms.ToTensor(),
                    transforms.Normalize(
                        mean=[0.485, 0.456, 0.406],
                        std=[0.229, 0.224, 0.225],
                    ),
                ]
            )

            tensor = transform(image)

    except ImagePreprocessingError:
        raise
    except (OSError, ValueError) as exc:
        raise ImagePreprocessingError(
            f"Unable to read image: {path.name}"
        ) from exc

    return tensor.unsqueeze(0)
