from pathlib import Path

import torch
import pytest
from PIL import Image

from ml.imaging.src.preprocess import (
    ImagePreprocessingError,
    preprocess_image,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
IMAGE_DIR = PROJECT_ROOT / "ml" / "imaging" / "data" / "images"


def test_real_chest_xray_preprocessing():
    image_path = next(IMAGE_DIR.glob("*.png"))

    result = preprocess_image(image_path)

    assert isinstance(result, torch.Tensor)
    assert result.shape == (1, 3, 224, 224)
    assert torch.isfinite(result).all()


def test_unsupported_format_is_rejected(tmp_path):
    image_path = tmp_path / "image.gif"
    image_path.write_bytes(b"fake image")

    with pytest.raises(ImagePreprocessingError, match="Unsupported image format"):
        preprocess_image(image_path)


def test_corrupt_png_is_rejected(tmp_path):
    image_path = tmp_path / "corrupt.png"
    image_path.write_bytes(b"not a valid PNG")

    with pytest.raises(ImagePreprocessingError):
        preprocess_image(image_path)


def test_missing_image_is_rejected(tmp_path):
    image_path = tmp_path / "missing.png"

    with pytest.raises(ImagePreprocessingError, match="not found"):
        preprocess_image(image_path)


def test_small_image_is_rejected(tmp_path):
    image_path = tmp_path / "small.png"
    Image.new("RGB", (16, 16)).save(image_path)

    with pytest.raises(ImagePreprocessingError, match="too small"):
        preprocess_image(image_path)


def test_invalid_image_size_is_rejected():
    image_path = next(IMAGE_DIR.glob("*.png"))

    with pytest.raises(ImagePreprocessingError, match="image_size"):
        preprocess_image(image_path, image_size=0)
    