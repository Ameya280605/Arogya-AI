"""Arogya AI — Roles, Permissions & Least-Privilege Policies.

Module 7, Phase 7.1: Roles & Permissions.
Defines canonical system roles (administrator, doctor_reviewer, researcher),
fine-grained permission grants, and centralized permission resolution logic.
"""

from enum import Enum


class RoleName(str, Enum):
    """Canonical system roles for Arogya AI."""

    ADMINISTRATOR = "administrator"
    DOCTOR_REVIEWER = "doctor_reviewer"
    RESEARCHER = "researcher"
    # Legacy alias from synthetic dev seed
    CLINICIAN = "clinician"


class Permission(str, Enum):
    """Fine-grained permission identifiers."""

    # Patient cohort operations
    PATIENT_READ = "patient:read"
    PATIENT_CREATE = "patient:create"
    PATIENT_UPDATE = "patient:update"
    PATIENT_DELETE = "patient:delete"

    # Clinical encounter operations
    ENCOUNTER_READ = "encounter:read"
    ENCOUNTER_CREATE = "encounter:create"
    ENCOUNTER_UPDATE = "encounter:update"

    # Physiological observations
    OBSERVATION_READ = "observation:read"
    OBSERVATION_CREATE = "observation:create"

    # AI & research analysis runs
    ANALYSIS_READ = "analysis:read"
    ANALYSIS_EXECUTE = "analysis:execute"

    # File and medical asset management
    ASSET_READ = "asset:read"
    ASSET_UPLOAD = "asset:upload"
    ASSET_DELETE = "asset:delete"

    # System administration and audit
    AUDIT_READ = "audit:read"
    USER_MANAGE = "user:manage"


# Centralized role-to-permission mapping adhering to least-privilege principles
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    RoleName.ADMINISTRATOR.value: {
        Permission.PATIENT_READ,
        Permission.PATIENT_CREATE,
        Permission.PATIENT_UPDATE,
        Permission.PATIENT_DELETE,
        Permission.ENCOUNTER_READ,
        Permission.ENCOUNTER_CREATE,
        Permission.ENCOUNTER_UPDATE,
        Permission.OBSERVATION_READ,
        Permission.OBSERVATION_CREATE,
        Permission.ANALYSIS_READ,
        Permission.ANALYSIS_EXECUTE,
        Permission.ASSET_READ,
        Permission.ASSET_UPLOAD,
        Permission.ASSET_DELETE,
        Permission.AUDIT_READ,
        Permission.USER_MANAGE,
    },
    RoleName.DOCTOR_REVIEWER.value: {
        Permission.PATIENT_READ,
        Permission.PATIENT_CREATE,
        Permission.PATIENT_UPDATE,
        Permission.ENCOUNTER_READ,
        Permission.ENCOUNTER_CREATE,
        Permission.ENCOUNTER_UPDATE,
        Permission.OBSERVATION_READ,
        Permission.OBSERVATION_CREATE,
        Permission.ANALYSIS_READ,
        Permission.ASSET_READ,
        Permission.ASSET_UPLOAD,
    },
    RoleName.CLINICIAN.value: {
        Permission.PATIENT_READ,
        Permission.PATIENT_CREATE,
        Permission.PATIENT_UPDATE,
        Permission.ENCOUNTER_READ,
        Permission.ENCOUNTER_CREATE,
        Permission.ENCOUNTER_UPDATE,
        Permission.OBSERVATION_READ,
        Permission.OBSERVATION_CREATE,
        Permission.ANALYSIS_READ,
        Permission.ASSET_READ,
        Permission.ASSET_UPLOAD,
    },
    RoleName.RESEARCHER.value: {
        # Researchers have read-only access to synthetic/research datasets and analyses
        Permission.PATIENT_READ,
        Permission.ENCOUNTER_READ,
        Permission.OBSERVATION_READ,
        Permission.ANALYSIS_READ,
        Permission.ASSET_READ,
    },
}


def get_permissions_for_roles(roles: list[str]) -> set[Permission]:
    """Resolve the union of all permissions granted across assigned roles.

    Args:
        roles: List of role names assigned to an identity.

    Returns:
        Set of unique Permission enums granted to the identity.
    """
    resolved: set[Permission] = set()
    for role in roles:
        cleaned = role.strip().lower()
        if cleaned in ROLE_PERMISSIONS:
            resolved.update(ROLE_PERMISSIONS[cleaned])
    return resolved


def has_permission(roles: list[str], permission: Permission | str) -> bool:
    """Check if the given roles satisfy the required permission.

    Args:
        roles: List of assigned role names.
        permission: Permission enum or string value to test.

    Returns:
        True if granted by at least one assigned role; False otherwise (deny by default).
    """
    perm_enum = Permission(permission) if isinstance(permission, str) else permission
    granted = get_permissions_for_roles(roles)
    return perm_enum in granted
