"""Arogya AI — Safe File Intake & Controlled Storage Service.

Module 7, Phase 7.5 & 7.6: Safe File Uploads & Storage.
Enforces:
- File size bounds (rejects 0-byte empty files and oversized payloads).
- Explicit allowlist of clinical media formats (PNG, JPEG, PDF, DICOM).
- Magic-byte / file-signature cryptographic inspection to prevent extension spoofing.
- Server-side UUID filename generation and path-traversal prevention.
- SHA-256 cryptographic digest calculation for payload integrity verification.
"""

from collections.abc import Generator
import hashlib
import logging
import os
from pathlib import Path
import re
import uuid

logger = logging.getLogger("arogya.services.storage")


class FileStorageError(Exception):
    """Base exception for file storage failures."""

    pass


class FileValidationError(FileStorageError):
    """Raised when an uploaded file violates format, size, or signature rules."""

    pass


class StorageService:
    """Service managing validated file intake, storage isolation, and safe retrieval."""

    # Explicit allowlist of supported extensions and associated MIME types
    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".dcm"}

    ALLOWED_MIME_TYPES = {
        "image/png": {".png"},
        "image/jpeg": {".jpg", ".jpeg"},
        "application/pdf": {".pdf"},
        "application/dicom": {".dcm"},
        "application/octet-stream": {".dcm"},  # Common generic binary stream for DICOM
    }

    # Canonical file signatures (magic bytes)
    PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
    JPEG_SIGNATURE = b"\xff\xd8\xff"
    PDF_SIGNATURE = b"%PDF"
    DICM_MAGIC = b"DICM"

    @classmethod
    def sanitize_original_filename(cls, filename: str | None) -> str:
        """Strip directory paths, control characters, and unsafe patterns from user filenames.

        Args:
            filename: Raw submitted filename from client.

        Returns:
            Sanitized, safe basename string.
        """
        if not filename or not filename.strip():
            return "unnamed_clinical_asset"

        # 1. Strip directory traversal tokens across POSIX and Windows
        base = os.path.basename(filename.replace("\\", "/"))

        # 2. Strip null bytes and non-printable characters
        cleaned = re.sub(r"[\x00-\x1f\x7f]", "", base).strip()

        # 3. Strip leading/trailing dots and spaces
        cleaned = cleaned.strip(". ")

        if not cleaned:
            return "unnamed_clinical_asset"

        # Cap length at 200 characters to preserve database bounds
        return cleaned[:200]

    @classmethod
    def validate_file_signature(cls, header: bytes, extension: str, media_type: str) -> None:
        """Inspect binary header magic bytes against claimed format.

        Args:
            header: Initial bytes of file (at least 256 bytes).
            extension: Lowercase extension with dot (e.g. '.png').
            media_type: Client MIME type.

        Raises:
            FileValidationError: If binary header fails format signature validation.
        """
        ext = extension.lower()

        if ext == ".png":
            if not header.startswith(cls.PNG_SIGNATURE):
                raise FileValidationError("File signature does not match PNG format specification")

        elif ext in {".jpg", ".jpeg"}:
            if not header.startswith(cls.JPEG_SIGNATURE):
                raise FileValidationError("File signature does not match JPEG format specification")

        elif ext == ".pdf":
            if not header.startswith(cls.PDF_SIGNATURE):
                raise FileValidationError("File signature does not match PDF format specification")

        elif ext == ".dcm":
            # DICOM files typically contain a 128-byte preamble followed by 'DICM'
            is_dicom = False
            if len(header) >= 132 and header[128:132] == cls.DICM_MAGIC:
                is_dicom = True
            elif header.startswith(cls.DICM_MAGIC):
                is_dicom = True

            if not is_dicom:
                raise FileValidationError("File signature does not match DICOM Part 10 medical format")

        else:
            raise FileValidationError(f"File extension '{ext}' is not permitted")

    @classmethod
    def validate_and_save(
        cls,
        *,
        file_bytes: bytes,
        original_filename: str,
        media_type: str | None,
        storage_base_dir: str | Path,
        max_size_bytes: int = 20 * 1024 * 1024,
    ) -> tuple[str, str, int, str, str]:
        """Validate payload bounds, signature, and write to server-side UUID storage path.

        Args:
            file_bytes: Complete binary payload.
            original_filename: Client filename.
            media_type: Claimed client MIME type.
            storage_base_dir: Root storage directory.
            max_size_bytes: Configured maximum file size limit in bytes.

        Returns:
            Tuple of:
            (relative_storage_path, safe_filename, safe_media_type, file_size_bytes, sha256_checksum)

        Raises:
            FileValidationError: If file fails validation rules.
        """
        file_size = len(file_bytes)

        # 1. Size bounds check
        if file_size == 0:
            raise FileValidationError("File is empty (0 bytes); rejected")

        if file_size > max_size_bytes:
            raise FileValidationError(
                f"File size ({file_size} bytes) exceeds maximum permitted limit of {max_size_bytes} bytes"
            )

        # 2. Filename and extension check
        safe_filename = cls.sanitize_original_filename(original_filename)
        _, ext = os.path.splitext(safe_filename)
        ext_lower = ext.lower()

        if not ext_lower or ext_lower not in cls.ALLOWED_EXTENSIONS:
            allowed = ", ".join(sorted(cls.ALLOWED_EXTENSIONS))
            raise FileValidationError(
                f"Disallowed file format '{ext_lower}'. Permitted formats: {allowed}"
            )

        # 3. MIME type normalization and verification
        clean_media = (media_type or "").strip().lower()
        if not clean_media or clean_media not in cls.ALLOWED_MIME_TYPES:
            # Fall back to canonical MIME type based on extension
            media_map = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".pdf": "application/pdf",
                ".dcm": "application/dicom",
            }
            clean_media = media_map.get(ext_lower, "application/octet-stream")

        # 4. Binary signature verification
        header_sample = file_bytes[:256]
        cls.validate_file_signature(header_sample, ext_lower, clean_media)

        # 5. Cryptographic SHA-256 integrity calculation
        hasher = hashlib.sha256()
        hasher.update(file_bytes)
        checksum = hasher.hexdigest()

        # 6. Server-side UUID filename generation (prevents overwrites and traversal)
        storage_dir = Path(storage_base_dir).resolve()
        storage_dir.mkdir(parents=True, exist_ok=True)

        asset_uuid = uuid.uuid4()
        storage_filename = f"{asset_uuid}{ext_lower}"
        target_path = (storage_dir / storage_filename).resolve()

        # Strict path traversal guarantee
        if not target_path.is_relative_to(storage_dir):
            raise FileValidationError("Security error: target path escapes designated storage root")

        # 7. Write binary payload
        with open(target_path, "wb") as f:
            f.write(file_bytes)

        # Relative storage locator stored in DB
        relative_storage_path = storage_filename

        return relative_storage_path, safe_filename, clean_media, file_size, checksum

    @classmethod
    def resolve_file_path(
        cls,
        relative_storage_path: str,
        storage_base_dir: str | Path,
    ) -> Path:
        """Resolve and verify an internal storage path against directory traversal.

        Args:
            relative_storage_path: Stored relative locator.
            storage_base_dir: Root storage directory.

        Returns:
            Resolved absolute Path if valid and existent.

        Raises:
            FileValidationError: If path escapes root directory or does not exist.
        """
        storage_dir = Path(storage_base_dir).resolve()
        target = (storage_dir / relative_storage_path).resolve()

        if not target.is_relative_to(storage_dir):
            raise FileValidationError("Security violation: path traversal attempt detected")

        if not target.exists() or not target.is_file():
            raise FileValidationError("Requested file does not exist on storage volume")

        return target
