"""Tests for the chest X-ray Grad-CAM pipeline."""

import os
import stat

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
    if os.name != "nt":
        assert stat.S_IMODE(output_path.parent.stat().st_mode) == 0o700
        assert stat.S_IMODE(output_path.stat().st_mode) == 0o600

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

@pytest.mark.parametrize(
    "label",
    ["Pneumonia", "Cardiomegaly", "Effusion"],
)
def test_gradcam_supports_multiple_labels(
    gradcam, sample_image, tmp_path, label
):
    output_path = tmp_path / f"gradcam_{label.lower()}.png"

    result = gradcam.generate(
        sample_image,
        label,
        output_path,
    )

    assert output_path.is_file()
    assert result["label"] == label
    assert np.isfinite(result["raw_model_score"])


@pytest.mark.parametrize(
    "image_size",
    [(128, 256), (512, 320)],
)
def test_gradcam_preserves_original_image_dimensions(
    gradcam, tmp_path, image_size
):
    width, height = image_size
    image_path = tmp_path / f"xray_{width}x{height}.png"

    image = np.random.default_rng(42).integers(
        0,
        256,
        size=(height, width),
        dtype=np.uint8,
    )
    Image.fromarray(image).save(image_path)

    output_path = tmp_path / "heatmap.png"

    gradcam.generate(
        image_path,
        "Pneumonia",
        output_path,
    )

    with Image.open(output_path) as result:
        assert result.size == image_size
        assert result.mode == "RGB"

def test_gradcam_supports_jpeg_images(gradcam, tmp_path):
    image_path = tmp_path / "sample_xray.jpg"

    image = np.random.default_rng(42).integers(
        0,
        256,
        size=(256, 256),
        dtype=np.uint8,
    )
    Image.fromarray(image).save(image_path, format="JPEG")

    output_path = tmp_path / "gradcam_jpeg.png"

    result = gradcam.generate(
        image_path,
        "Pneumonia",
        output_path,
    )

    assert output_path.is_file()
    assert result["label"] == "Pneumonia"

    with Image.open(output_path) as output:
        assert output.format == "PNG"
        assert output.size == (256, 256)


def test_gradcam_rejects_corrupted_image(gradcam, tmp_path):
    image_path = tmp_path / "corrupted.png"
    image_path.write_bytes(b"This is not a valid image")

    with pytest.raises(GradCAMError, match="corrupt or cannot be decoded"):
        gradcam.generate(
            image_path,
            "Pneumonia",
            tmp_path / "corrupted_output.png",
        )