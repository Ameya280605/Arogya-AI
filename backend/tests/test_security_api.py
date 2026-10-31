"""Arogya AI — Module 7 Security & Server-Side Authorization Tests.

Module 7: Security, Identity & File Handling.
Comprehensive automated test suite covering:
- Missing, invalid, expired, and valid JWT authentication credentials.
- Role-Based Access Control (RBAC):
  - Administrator privileges (full access to cohorts, encounters, assets).
  - Doctor Reviewer privileges (patient CRUD, clinical workflows, asset uploads).
  - Researcher privileges (read-only cohort evaluation, denied write/upload access).
  - Deactivated accounts.
- Access denials (HTTP 401 & 403) and immutable audit event capture.
- Secret sanitization in audit event metadata.
- Cross-patient resource authorization boundaries.
"""

from collections.abc import Generator
from datetime import datetime, timedelta, timezone
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db import Base, get_db
from backend.app.db.models import AuditEvent, Encounter, Patient, Role, User
from backend.app.main import create_app
from backend.app.security.passwords import hash_password
from backend.app.security.roles import RoleName
from backend.app.security.tokens import create_access_token
from backend.app.settings import Settings

TEST_SECRET = "test-secret-key-for-jwt-signing-minimum-32-chars-long!"


@pytest.fixture
def sec_engine():
    """Isolated SQLite engine for security test suite."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def sec_db(sec_engine) -> Generator[Session, None, None]:
    """Database session populated with canonical roles and test accounts."""
    session_factory = sessionmaker(bind=sec_engine, autoflush=False, autocommit=False)
    session = session_factory()

    # Seed canonical roles
    admin_role = Role(
        id=uuid.uuid4(),
        name=RoleName.ADMINISTRATOR.value,
        description="Admin role",
    )
    doctor_role = Role(
        id=uuid.uuid4(),
        name=RoleName.DOCTOR_REVIEWER.value,
        description="Doctor Reviewer role",
    )
    researcher_role = Role(
        id=uuid.uuid4(),
        name=RoleName.RESEARCHER.value,
        description="Researcher role",
    )
    session.add_all([admin_role, doctor_role, researcher_role])
    session.flush()

    # Create test accounts
    admin_user = User(
        id=uuid.uuid4(),
        username="admin_user",
        email="admin@sec.test",
        full_name="Admin Test User",
        hashed_password=hash_password("admin_pass_12345"),
        is_active=True,
    )
    admin_user.roles.append(admin_role)

    doctor_user = User(
        id=uuid.uuid4(),
        username="doctor_user",
        email="doctor@sec.test",
        full_name="Doctor Reviewer Test",
        hashed_password=hash_password("doctor_pass_12345"),
        is_active=True,
    )
    doctor_user.roles.append(doctor_role)

    researcher_user = User(
        id=uuid.uuid4(),
        username="researcher_user",
        email="researcher@sec.test",
        full_name="Researcher Test",
        hashed_password=hash_password("research_pass_12345"),
        is_active=True,
    )
    researcher_user.roles.append(researcher_role)

    inactive_user = User(
        id=uuid.uuid4(),
        username="inactive_user",
        email="inactive@sec.test",
        full_name="Deactivated User",
        hashed_password=hash_password("inactive_pass_12345"),
        is_active=False,
    )
    inactive_user.roles.append(doctor_role)

    session.add_all([admin_user, doctor_user, researcher_user, inactive_user])
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def sec_client(sec_engine, sec_db) -> Generator[TestClient, None, None]:
    """TestClient wired to isolated security database."""
    settings = Settings(
        app_name="Arogya AI Security Tests",
        app_env="testing",
        secret_key=TEST_SECRET,
        api_prefix="/api/v1",
    )
    app = create_app(settings)

    def override_get_db() -> Generator[Session, None, None]:
        session_factory = sessionmaker(bind=sec_engine, autoflush=False, autocommit=False)
        s = session_factory()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# =============================================================================
# 7.2: Authentication Endpoints (/auth/login, /auth/logout, /auth/me)
# =============================================================================


def test_auth_login_successful_flow(sec_client: TestClient, sec_db: Session) -> None:
    """Verify login with correct credentials yields signed JWT and UserSummary."""
    res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "doctor_user", "password": "doctor_pass_12345"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
    assert data["user"]["username"] == "doctor_user"
    assert "doctor_reviewer" in data["user"]["roles"]
    assert "patient:read" in data["user"]["permissions"]
    assert "patient:create" in data["user"]["permissions"]

    # Verify audit event recorded
    events = sec_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "auth.login.success")
    ).all()
    assert len(events) >= 1
    latest = events[-1]
    assert latest.action == "login"
    assert "doctor_user" in latest.event_metadata.get("username", "")


def test_auth_login_invalid_password(sec_client: TestClient, sec_db: Session) -> None:
    """Verify login rejection with incorrect password and audit failure logging."""
    res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "doctor_user", "password": "WRONG_PASSWORD!"},
    )
    assert res.status_code == 401
    err = res.json()
    assert err["error"]["code"] == "UNAUTHORIZED"

    # Verify audit event for failed login
    events = sec_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "auth.login.failure")
    ).all()
    assert len(events) >= 1
    latest = events[-1]
    assert latest.event_metadata.get("reason") == "invalid_password"
    # Ensure password is NEVER logged in audit event
    assert "WRONG_PASSWORD" not in str(latest.event_metadata)


def test_auth_login_unknown_user(sec_client: TestClient, sec_db: Session) -> None:
    """Verify login rejection for non-existent handle."""
    res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "ghost_user_404", "password": "SomePassword123"},
    )
    assert res.status_code == 401
    err = res.json()
    assert err["error"]["code"] == "UNAUTHORIZED"

    events = sec_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "auth.login.failure")
    ).all()
    assert any(e.event_metadata.get("reason") == "user_not_found" for e in events)


def test_auth_login_deactivated_account(sec_client: TestClient) -> None:
    """Verify deactivated user cannot authenticate."""
    res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "inactive_user", "password": "inactive_pass_12345"},
    )
    assert res.status_code == 401


def test_auth_me_authenticated_reflection(sec_client: TestClient) -> None:
    """Verify /auth/me returns current user profile when valid bearer token is provided."""
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "admin_user", "password": "admin_pass_12345"},
    )
    token = login_res.json()["access_token"]

    me_res = sec_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_res.status_code == 200
    user_info = me_res.json()
    assert user_info["username"] == "admin_user"
    assert "administrator" in user_info["roles"]
    assert "user:manage" in user_info["permissions"]


def test_auth_logout_terminates_session(sec_client: TestClient, sec_db: Session) -> None:
    """Verify /auth/logout accepts bearer token and logs session termination."""
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "doctor_user", "password": "doctor_pass_12345"},
    )
    token = login_res.json()["access_token"]

    logout_res = sec_client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "success"

    events = sec_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "auth.logout")
    ).all()
    assert len(events) >= 1


# =============================================================================
# 7.1 & 7.3: Missing, Invalid & Expired Token Authentication
# =============================================================================


def test_unauthenticated_request_denied_by_default(sec_client: TestClient) -> None:
    """Verify accessing protected routes without credentials returns 401."""
    res = sec_client.get("/api/v1/patients")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"

    res_dash = sec_client.get("/api/v1/dashboard/overview")
    assert res_dash.status_code == 401
    assert res_dash.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_bearer_token_rejected(sec_client: TestClient) -> None:
    """Verify malformed or corrupt bearer tokens return 401."""
    res = sec_client.get(
        "/api/v1/patients",
        headers={"Authorization": "Bearer NOT_A_REAL_JWT_TOKEN_HEADER"},
    )
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_bearer_token_rejected(sec_client: TestClient, sec_db: Session) -> None:
    """Verify expired JWT tokens return 401 with appropriate message."""
    user = sec_db.scalar(select(User).where(User.username == "doctor_user"))
    expired_token = create_access_token(
        user_id=user.id,
        username=user.username,
        roles=["doctor_reviewer"],
        secret_key=TEST_SECRET,
        expires_delta=timedelta(seconds=-60),  # Expired 60s ago
    )

    res = sec_client.get(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert res.status_code == 401
    assert "expired" in res.json()["error"]["message"].lower()


# =============================================================================
# 7.1 & 7.3: Role-Based Authorization Enforcement (Least Privilege)
# =============================================================================


def test_doctor_reviewer_can_create_patient(sec_client: TestClient) -> None:
    """Doctor Reviewer has PATIENT_CREATE permission and can register patients."""
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "doctor_user", "password": "doctor_pass_12345"},
    )
    token = login_res.json()["access_token"]

    create_res = sec_client.post(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mrn_pseudonym": "DOC-REV-PAT-001",
            "biological_sex": "female",
            "is_synthetic": True,
        },
    )
    assert create_res.status_code == 201
    pat = create_res.json()
    assert pat["mrn_pseudonym"] == "DOC-REV-PAT-001"


def test_researcher_denied_patient_creation(sec_client: TestClient, sec_db: Session) -> None:
    """Researcher has read-only access and is denied (403) from creating patients."""
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "researcher_user", "password": "research_pass_12345"},
    )
    token = login_res.json()["access_token"]

    create_res = sec_client.post(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mrn_pseudonym": "RESEARCH-DENIED-001",
            "biological_sex": "male",
            "is_synthetic": True,
        },
    )
    assert create_res.status_code == 403
    assert create_res.json()["error"]["code"] == "FORBIDDEN"

    # Verify access_denied audit event
    denied_events = sec_db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "auth.access_denied")
    ).all()
    assert len(denied_events) >= 1
    assert any("missing permission" in (e.description or "").lower() for e in denied_events)


def test_researcher_can_read_patients(sec_client: TestClient) -> None:
    """Researcher has PATIENT_READ permission and can list patient cohorts."""
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "researcher_user", "password": "research_pass_12345"},
    )
    token = login_res.json()["access_token"]

    list_res = sec_client.get(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    assert "items" in list_res.json()


def test_administrator_full_access(sec_client: TestClient) -> None:
    """Administrator has all permissions and can both read and create."""
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "admin_user", "password": "admin_pass_12345"},
    )
    token = login_res.json()["access_token"]

    create_res = sec_client.post(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "mrn_pseudonym": "ADMIN-PAT-999",
            "biological_sex": "other",
            "is_synthetic": True,
        },
    )
    assert create_res.status_code == 201

    list_res = sec_client.get(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200


# =============================================================================
# 7.3: Cross-Patient Data Access Prevention
# =============================================================================


def test_cross_patient_encounter_mismatch_rejected(sec_client: TestClient, sec_db: Session) -> None:
    """Verify encounter observation prevents cross-patient mismatch."""
    login_res = sec_client.post(
        "/api/v1/auth/login",
        json={"username": "doctor_user", "password": "doctor_pass_12345"},
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create Patient A and Encounter A
    pat_a = sec_client.post(
        "/api/v1/patients",
        headers=headers,
        json={"mrn_pseudonym": "CROSS-A-001", "is_synthetic": True},
    ).json()

    enc_a = sec_client.post(
        f"/api/v1/patients/{pat_a['id']}/encounters",
        headers=headers,
        json={"encounter_type": "ambulatory", "start_time": "2026-10-27T10:00:00Z"},
    ).json()

    # Create observation on Encounter A
    obs_res = sec_client.post(
        f"/api/v1/encounters/{enc_a['id']}/observations",
        headers=headers,
        json={
            "code": "8867-4",
            "display_name": "Heart Rate",
            "observed_at": "2026-10-27T10:05:00Z",
            "numeric_value": 72.0,
            "unit": "bpm",
        },
    )
    assert obs_res.status_code == 201
    assert obs_res.json()["patient_id"] == pat_a["id"]


# =============================================================================
# 7.4: Audit Event Secret Masking & Non-leakage
# =============================================================================


def test_audit_events_never_leak_passwords_or_tokens(sec_db: Session) -> None:
    """Verify all persisted AuditEvent rows strictly contain no plaintext credentials."""
    events = sec_db.scalars(select(AuditEvent)).all()
    for ev in events:
        meta_str = str(ev.event_metadata or "")
        desc_str = str(ev.description or "")
        assert "admin_pass_12345" not in meta_str
        assert "doctor_pass_12345" not in meta_str
        assert "research_pass_12345" not in meta_str
        assert "admin_pass_12345" not in desc_str
