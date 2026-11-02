"""Tests for private storage directory and file permissions."""

import os
import stat

from backend.app.services.storage import StorageService


def test_upload_storage_is_private(tmp_path):
    storage_dir = tmp_path / "uploads"
    payload = StorageService.PNG_SIGNATURE + b"test"

    relative_path, _, _, _, _ = StorageService.validate_and_save(
        file_bytes=payload,
        original_filename="chest.png",
        media_type="image/png",
        storage_base_dir=storage_dir,
    )
    stored_path = StorageService.resolve_file_path(
        relative_path,
        storage_dir,
    )

    assert stored_path.read_bytes() == payload
    if os.name != "nt":
        assert stat.S_IMODE(storage_dir.stat().st_mode) == 0o700
        assert stat.S_IMODE(stored_path.stat().st_mode) == 0o600
