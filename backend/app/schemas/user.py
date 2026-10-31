"""Arogya AI - User & Role API Schemas.

Module 3, Phase 3.4: Pydantic Request/Response Schemas & Data Contracts.
Defines contracts for User and Role management. Plaintext passwords are only
accepted on creation/credential submission and are strictly excluded from response models.
Database-internal hashed_password fields are never exposed.
"""

from datetime import datetime
from uuid import UUID
from pydantic import Field
from backend.app.schemas.common import BaseSchema, ORMModel


# ---------------------------------------------------------------------------
# Role Contracts
# ---------------------------------------------------------------------------


class RoleBase(BaseSchema):
    """Base schema attributes for authorization roles."""

    name: str = Field(
        min_length=1,
        max_length=64,
        description="Unique role name (e.g. 'administrator', 'clinician', 'researcher')",
        examples=["clinician"],
    )
    description: str | None = Field(
        default=None,
        max_length=255,
        description="Human-readable role description",
        examples=["Reviewing clinician with case sign-off authority"],
    )


class RoleCreate(RoleBase):
    """Request contract for creating a new system role."""

    pass


class RoleResponse(RoleBase, ORMModel):
    """Response contract representing a system role."""

    id: UUID = Field(
        description="Unique role identifier",
    )
    created_at: datetime = Field(
        description="Role creation timestamp in UTC",
    )


# ---------------------------------------------------------------------------
# User Contracts
# ---------------------------------------------------------------------------


class UserBase(BaseSchema):
    """Base schema attributes for user accounts."""

    username: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_\-\.]+$",
        description="Unique alphanumeric login handle",
        examples=["dr_smith"],
    )
    email: str = Field(
        min_length=5,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="User email address for communications and notifications",
        examples=["dr_smith@hospital.org"],
    )
    full_name: str = Field(
        min_length=1,
        max_length=128,
        description="Full display name of the user",
        examples=["Dr. Sarah Smith"],
    )


class UserCreate(UserBase):
    """Request contract for creating/registering a user account.

    The password field is accepted for credential generation; it is never returned
    in responses.
    """

    password: str = Field(
        min_length=8,
        max_length=128,
        description="Account password (minimum 8 characters)",
    )
    role_ids: list[UUID] | None = Field(
        default=None,
        description="Optional list of role UUIDs to assign upon creation",
    )


class UserUpdate(BaseSchema):
    """Request contract for updating user account attributes."""

    email: str | None = Field(
        default=None,
        min_length=5,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="Updated user email address",
    )
    full_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        description="Updated full display name",
    )
    is_active: bool | None = Field(
        default=None,
        description="Account activation status",
    )
    role_ids: list[UUID] | None = Field(
        default=None,
        description="Updated set of assigned role UUIDs",
    )


class UserResponse(UserBase, ORMModel):
    """Response contract representing a user profile.

    Security Notice:
    - Never includes 'password' or 'hashed_password'.
    - Server-controlled timestamps and identity fields are read-only.
    """

    id: UUID = Field(
        description="Unique user identifier",
    )
    is_active: bool = Field(
        description="Account active state",
    )
    created_at: datetime = Field(
        description="Account creation timestamp in UTC",
    )
    updated_at: datetime = Field(
        description="Account last-modified timestamp in UTC",
    )
    roles: list[RoleResponse] = Field(
        default_factory=list,
        description="List of assigned authorization roles",
    )
