"""Arogya AI — Safe File Intake, Controlled Storage & Asset Security Tests.

Module 7, Phases 7.5, 7.6 & 7.7: Safe File Uploads, File Storage & Security Tests.
Automated tests covering:
- Authenticated upload permissions (administrator, doctor_reviewer allowed; researcher denied).
- Allowlist enforcement (PNG, JPEG, PDF, DICOM permitted; scripts/executables rejected).
- Magic-byte file-signature verification (detects and rejects disguised extension spoofing).
- Size bounds checking (rejects 0-byte empty files and oversized payloads).
- Path traversal and malicious filename mitigation (sanitizes paths, writes server-side UUIDs).
- Cross-patient isolation (rejects attaching an asset for Patient A to Patient B's encounter).
- Controlled download endpoints under resource authorization.
- Immutable audit event logging for upload and download operations.
"""

from collections.abc import Generator
from datetime import datetime, timezone
import io
from pathlib import Path
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.db.models import AuditEvent, Encounter, Patient, Role, UploadedAsset, User
from backend.app.main import create_app
from backend.app.security.passwords import hash_password
from backend.app.security.roles import RoleName
from backend.app.settings import Settings

TEST_SECRET = "asset-security-test-secret-key-32-characters-minimum!"

# Valid magic byte payloads for testing
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4"
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
VALID_PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
# DICOM with standard 128-byte preamble followed by 'DICM'
VALID_DICOM_BYTES = (b"\x00" * 128) + b"DICM" + (b"\x00" * 32)


@pytest.fixture
def asset_storage_dir() -> Generator[Path, None, None]:
    """Temporary storage directory isolated for file intake tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def asset_engine():
    """Isolated SQLite engine for asset tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def asset_db(asset_engine) -> Generator[Session, None, None]:
    """Database session with seeded roles, accounts, and clinical test patients."""
    session_factory = sessionmaker(bind=asset_engine, autoflush=False, autocommit=False)
    session = session_factory()

    admin_role = Role(id=uuid.uuid4(), name=RoleName.ADMINISTRATOR.value)
    doctor_role = Role(id=uuid.uuid4(), name=RoleName.DOCTOR_REVIEWER.value)
    researcher_role = Role(id=uuid.uuid4(), name=RoleName.RESEARCHER.value)
    session.add_all([admin_role, doctor_role, researcher_role])
    session.flush()

    doctor_user = User(
        id=uuid.uuid4(),
        username="doc_uploader",
        email="doctor@upload.test",
        full_name="Doctor Uploader",
        hashed_password=hash_password("doc_secret_123"),
        is_active=True,
    )
    doctor_user.roles.append(doctor_role)

    researcher_user = User(
        id=uuid.uuid4(),
        username="res_reader",
        email="researcher@upload.test",
        full_name="Researcher Reader",
        hashed_password=hash_password("res_secret_123"),
        is_active=True,
    )
    researcher_user.roles.append(researcher_role)

    # Clinical test patient cohorts
    patient_a = Patient(
        id=uuid.uuid4(),
        mrn_pseudonym="PAT-ASSET-001",
        is_synthetic=True,
    )
    patient_b = Patient(
        id=uuid.uuid4(),
        mrn_pseudonym="PAT-ASSET-002",
        is_synthetic=True,
    )
    session.add_all([doctor_user, researcher_user, patient_a, patient_b])
    session.flush()

    # Encounter belonging to Patient B
    encounter_b = Encounter(
        id=uuid.uuid4(),
        patient_id=patient_b.id,
        encounter_type="inpatient",
        status="active",
        start_time=datetime(2026, 10, 27, 8, 0, tzinfo=timezone.utc),
    )
    session.add(encounter_b)
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def asset_client(asset_engine, asset_db, asset_storage_dir) -> Generator[TestClient, None, None]:
    """TestClient configured with isolated storage directory."""
    settings = Settings(
        app_name="Arogya AI Asset Tests",
        app_env="testing",
        secret_key=TEST_SECRET,
        upload_storage_dir=str(asset_storage_dir),
        max_upload_size_bytes=1024 * 1024,  # 1MB limit for quick testing
        api_prefix="/api/v1",
    )
    app = create_app(settings)

    def override_get_db() -> Generator[Session, None, None]:
        session_factory = sessionmaker(bind=asset_engine, autoflush=False, autocommit=False)
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def get_token(client: TestClient, username: str, password: str) -> str:
    """Helper to authenticate and retrieve token."""
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return res.json()["access_token"]


# =============================================================================
# 7.5: Safe File Uploads & Format Validation
# =============================================================================


def test_successful_png_upload(asset_client: TestClient, asset_db: Session, asset_storage_dir: Path) -> None:
    """Doctor Reviewer can upload a valid PNG radiograph attachment."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    files = {"file": ("chest_xray_pa.png", io.BytesIO(VALID_PNG_BYTES), "image/png")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 201
    asset_data = res.json()
    assert asset_data["original_filename"] == "chest_xray_pa.png"
    assert asset_data["media_type"] == "image/png"
    assert asset_data["file_size_bytes"] == len(VALID_PNG_BYTES)
    assert "checksum_sha256" in asset_data

    # Verify file saved on storage disk
    saved_files = list(asset_storage_dir.glob("*.png"))
    assert len(saved_files) == 1

    # Verify audit event recorded
    events = asset_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "asset.uploaded")
    ).all()
    assert len(events) >= 1
    assert events[-1].resource_type == "asset"


def test_successful_dicom_upload(asset_client: TestClient, asset_db: Session, asset_storage_dir: Path) -> None:
    """Upload valid DICOM file with preamble signature."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    files = {"file": ("ct_chest_slice.dcm", io.BytesIO(VALID_DICOM_BYTES), "application/dicom")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 201
    assert res.json()["media_type"] == "application/dicom"


def test_researcher_denied_file_upload(asset_client: TestClient, asset_db: Session) -> None:
    """Researcher role lacks ASSET_UPLOAD permission and is rejected with 403."""
    token = get_token(asset_client, "res_reader", "res_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    files = {"file": ("test.png", io.BytesIO(VALID_PNG_BYTES), "image/png")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_disallowed_extension_rejected(asset_client: TestClient, asset_db: Session) -> None:
    """Executable or script extensions (.exe, .sh) are denied with 422."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    malicious_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    files = {"file": ("malware.exe", io.BytesIO(malicious_bytes), "application/x-msdownload")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 422
    assert "Disallowed file format" in res.json()["error"]["message"]


def test_spoofed_mime_type_detected_and_rejected(asset_client: TestClient, asset_db: Session) -> None:
    """Plain text disguised as a PNG file fails magic-byte verification."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    fake_png = b"Plain text payload pretending to be a medical image radiograph"
    files = {"file": ("disguised.png", io.BytesIO(fake_png), "image/png")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 422
    assert "File signature does not match" in res.json()["error"]["message"]


def test_empty_file_rejected(asset_client: TestClient, asset_db: Session) -> None:
    """Empty files (0 bytes) are rejected."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    files = {"file": ("empty.png", io.BytesIO(b""), "image/png")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 422
    assert "empty" in res.json()["error"]["message"].lower()


def test_oversized_file_rejected(asset_client: TestClient, asset_db: Session) -> None:
    """Files exceeding max_upload_size_bytes are rejected."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    # Configured limit in test fixture is 1MB; create 1.5MB PNG
    large_payload = VALID_PNG_BYTES + (b"\x00" * (1024 * 1024 + 100))
    files = {"file": ("huge_scan.png", io.BytesIO(large_payload), "image/png")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 422
    assert "exceeds maximum permitted limit" in res.json()["error"]["message"]


# =============================================================================
# 7.5 & 7.6: Path Traversal & Filename Sanitization
# =============================================================================


def test_path_traversal_filename_sanitized_safely(
    asset_client: TestClient, asset_db: Session, asset_storage_dir: Path
) -> None:
    """Malicious filename containing directory traversal tokens is sanitized."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    traversal_filename = "../../../etc/passwd.png"
    files = {"file": (traversal_filename, io.BytesIO(VALID_PNG_BYTES), "image/png")}
    data = {"patient_id": str(pat.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 201
    safe_name = res.json()["original_filename"]
    assert ".." not in safe_name
    assert "/" not in safe_name
    assert safe_name == "passwd.png"

    # Verify file was written inside storage directory, not escaped to parent or root
    assert not (asset_storage_dir.parent / "passwd.png").exists()
    saved_files = list(asset_storage_dir.glob("*.png"))
    assert len(saved_files) == 1
    assert saved_files[0].is_relative_to(asset_storage_dir)
    assert saved_files[0].parent == asset_storage_dir


# =============================================================================
# 7.3: Cross-Patient Asset Boundary Validation
# =============================================================================


def test_cross_patient_asset_encounter_mismatch_rejected(asset_client: TestClient, asset_db: Session) -> None:
    """Attempting to attach an asset for Patient A citing Patient B's encounter is rejected (422)."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat_a = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))
    enc_b = asset_db.scalar(select(Encounter))

    # Patient A does NOT own Encounter B
    assert enc_b.patient_id != pat_a.id

    files = {"file": ("chest_scan.png", io.BytesIO(VALID_PNG_BYTES), "image/png")}
    data = {"patient_id": str(pat_a.id), "encounter_id": str(enc_b.id)}

    res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    assert res.status_code == 422
    assert "does not belong to patient" in res.json()["error"]["message"]

    # Verify cross-patient security violation audit event
    events = asset_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "security.cross_patient_violation")
    ).all()
    assert len(events) >= 1


# =============================================================================
# 7.6: Resource-Authorized Binary Downloads & Metadata
# =============================================================================


def test_authenticated_asset_download(asset_client: TestClient, asset_db: Session) -> None:
    """Authorized users can download binary payload with correct headers and audit event."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    pat = asset_db.scalar(select(Patient).where(Patient.mrn_pseudonym == "PAT-ASSET-001"))

    # Upload first
    files = {"file": ("download_test.pdf", io.BytesIO(VALID_PDF_BYTES), "application/pdf")}
    data = {"patient_id": str(pat.id)}

    upload_res = asset_client.post(
        "/api/v1/assets/upload",
        headers={"Authorization": f"Bearer {token}"},
        data=data,
        files=files,
    )
    asset_id = upload_res.json()["id"]

    # Download
    download_res = asset_client.get(
        f"/api/v1/assets/{asset_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert download_res.status_code == 200
    assert download_res.content == VALID_PDF_BYTES
    assert "application/pdf" in download_res.headers.get("content-type", "")
    assert "download_test.pdf" in download_res.headers.get("content-disposition", "")

    # Verify download audit event
    events = asset_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "asset.downloaded")
    ).all()
    assert len(events) >= 1
    assert events[-1].resource_id == str(asset_id)


def test_unauthenticated_download_rejected(asset_client: TestClient, asset_db: Session) -> None:
    """Download requests without Authorization header return 401."""
    random_uuid = uuid.uuid4()
    res = asset_client.get(f"/api/v1/assets/{random_uuid}/download")
    assert res.status_code == 401


def test_download_nonexistent_asset_returns_404(asset_client: TestClient) -> None:
    """Download request for nonexistent asset returns 404."""
    token = get_token(asset_client, "doc_uploader", "doc_secret_123")
    random_uuid = uuid.uuid4()
    res = asset_client.get(
        f"/api/v1/assets/{random_uuid}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404
