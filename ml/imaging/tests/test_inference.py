"""Tests for the chest X-ray inference pipeline."""

import numpy as np
import pytest
import torch
import torchxrayvision as xrv
from PIL import Image

from ml.imaging.src.inference import (
    ChestXrayInference,
    ImagingInferenceError,
)

@pytest.fixture(scope="module")
def pipeline():
    """Load the model once for this test module."""
    return ChestXrayInference()

@pytest.fixture
def valid_image(tmp_path):
    """Create a synthetic grayscale image for input validation tests."""
    path = tmp_path / "test_xray.png"
    image = Image.fromarray(
        np.random.default_rng(42).integers(
            0, 256, size=(256, 256), dtype=np.uint8
        )
    )
    image.save(path)
    return path

def test_preprocess_returns_expected_shape(valid_image):
    tensor = ChestXrayInference.preprocess(valid_image)

    assert isinstance(tensor, torch.Tensor)
    assert tuple(tensor.shape) == (1, 1, 224, 224)
    assert torch.isfinite(tensor).all()

def test_checkpoint_path_uses_cache_metadata_without_loading_model(
    monkeypatch, tmp_path
):
    checkpoint_name = "nih-checkpoint.pt"
    monkeypatch.setattr(xrv.utils, "get_cache_dir", lambda: str(tmp_path))
    monkeypatch.setitem(
        xrv.models.model_urls,
        ChestXrayInference.MODEL_WEIGHTS,
        {"weights_url": f"https://models.invalid/{checkpoint_name}"},
    )
    monkeypatch.setattr(
        xrv.models,
        "DenseNet",
        lambda **kwargs: pytest.fail("checkpoint lookup must not load weights"),
    )

    assert ChestXrayInference.checkpoint_path() == tmp_path / checkpoint_name

def test_rejects_unsupported_format(tmp_path):
    path = tmp_path / "image.gif"
    path.write_bytes(b"not a real image")

    with pytest.raises(ImagingInferenceError, match="Unsupported format"):
        ChestXrayInference.preprocess(path)

def test_rejects_missing_file(tmp_path):
    path = tmp_path / "missing.png"

    with pytest.raises(ImagingInferenceError, match="not found"):
        ChestXrayInference.preprocess(path)

def test_rejects_corrupt_image(tmp_path):
    path = tmp_path / "corrupt.png"
    path.write_bytes(b"this is not a valid PNG image")

    with pytest.raises(ImagingInferenceError, match="corrupt"):
        ChestXrayInference.preprocess(path)

def test_rejects_tiny_image(tmp_path):
    path = tmp_path / "tiny.png"
    Image.new("L", (16, 16)).save(path)

    with pytest.raises(ImagingInferenceError, match="at least 32x32"):
        ChestXrayInference.preprocess(path)

def test_rejects_oversized_file(tmp_path):
    path = tmp_path / "large.png"

    # Sparse file larger than the 20 MB upload limit.
    with path.open("wb") as file:
        file.seek(20 * 1024 * 1024)
        file.write(b"x")

    with pytest.raises(ImagingInferenceError, match="20 MB"):
        ChestXrayInference.preprocess(path)

def test_model_returns_14_finite_scores(pipeline, valid_image):
    result = pipeline.predict(valid_image)

    assert result["research_only"] is True
    assert result["model"] == "densenet121-res224-nih"
    assert len(result["predictions"]) == 14

    labels = [item["label"] for item in result["predictions"]]
    scores = [item["score"] for item in result["predictions"]]

    assert len(set(labels)) == 14
    assert all(np.isfinite(scores))
    assert all(isinstance(score, float) for score in scores)

def test_result_does_not_claim_calibrated_probabilities(
    pipeline, valid_image
):
    result = pipeline.predict(valid_image)

    assert (
        result["output_type"]
        == "raw_model_scores_not_calibrated_probabilities"
    )

def test_model_inference_failure_is_reported(pipeline, valid_image, monkeypatch):
    def fail_inference(*args, **kwargs):
        raise RuntimeError("simulated model failure")

    monkeypatch.setattr(pipeline.model, "forward", fail_inference)

    with pytest.raises(RuntimeError, match="inference failed"):
        pipeline.predict(valid_image)
