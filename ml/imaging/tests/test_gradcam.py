"""Tests for the chest X-ray Grad-CAM pipeline."""

import numpy as np
import pytest
import torch
from PIL import Image

from ml.imaging.src.gradcam import ChestXrayGradCAM, GradCAMError


@pytest.fixture(scope="module")
def gradcam():
    """Load the pretrained model once for this test module."""
    return ChestXrayGradCAM()


@pytest.fixture
def sample_image(tmp_path):
    """Create a synthetic RGB image for preprocessing tests."""
    image_path = tmp_path / "sample_xray.png"

    image = np.random.default_rng(42).integers(
        0, 256, size=(256, 256), dtype=np.uint8
    )
    Image.fromarray(image).save(image_path)

    return image_path


def test_gradcam_generates_overlay(gradcam, sample_image, tmp_path):
    output_path = tmp_path / "gradcam_overlay.png"

    result = gradcam.generate(
        sample_image,
        "Pneumonia",
        output_path,
    )

    assert output_path.is_file()
    assert result["label"] == "Pneumonia"
    assert result["research_only"] is True
    assert np.isfinite(result["raw_model_score"])

    with Image.open(output_path) as output:
        assert output.format == "PNG"
        assert output.size == (256, 256)
        assert output.mode == "RGB"


def test_gradcam_rejects_unknown_label(gradcam, sample_image, tmp_path):
    with pytest.raises(GradCAMError, match="Unknown label"):
        gradcam.generate(
            sample_image,
            "UnknownDisease",
            tmp_path / "invalid.png",
        )


def test_gradcam_rejects_missing_image(gradcam, tmp_path):
    with pytest.raises(GradCAMError, match="Image file not found"):
        gradcam.generate(
            tmp_path / "missing.png",
            "Pneumonia",
            tmp_path / "missing_output.png",
        )


def test_gradcam_rejects_invalid_output_extension(
    gradcam, sample_image, tmp_path
):
    with pytest.raises(GradCAMError, match="Output must be"):
        gradcam.generate(
            sample_image,
            "Pneumonia",
            tmp_path / "output.txt",
        )
