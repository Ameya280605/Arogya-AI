"""Arogya AI — Authentication & Identity Pydantic Schemas.

Module 7, Phase 7.2: Authentication & Protected Routes.
Defines typed request/response contracts for user login, token exchange,
current-user profile retrieval, and role/permission reflections.
"""

from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field


class LoginPayload(BaseModel):
    """Payload submitted to authenticate and retrieve an access token."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="User login username handle or email address",
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Plaintext candidate password",
    )


class UserSummary(BaseModel):
    """Safe public representation of an authenticated user identity."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique user UUID identifier",
    )
    username: str = Field(
        ...,
        description="Canonical user handle",
    )
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        pattern=r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        description="User email address",
    )
    full_name: str = Field(
        ...,
        description="Display name",
    )
    is_active: bool = Field(
        ...,
        description="Active account status",
    )
    roles: list[str] = Field(
        default_factory=list,
        description="Assigned role names",
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Computed permission capabilities granted to identity",
    )
    created_at: datetime = Field(
        ...,
        description="Account registration timestamp in UTC",
    )


class TokenResponse(BaseModel):
    """Successful authentication response containing JWT access token."""

    access_token: str = Field(
        ...,
        description="Signed compact JWT access token",
    )
    token_type: str = Field(
        default="bearer",
        description="Token authorization scheme (Bearer)",
    )
    expires_in: int = Field(
        ...,
        description="Token validity duration in seconds",
    )
    user: UserSummary = Field(
        ...,
        description="Profile metadata for the authenticated user",
    )


class LogoutResponse(BaseModel):
    """Confirmation payload returned on user session termination."""

    status: str = Field(
        default="success",
        description="Logout operation status indicator",
    )
    message: str = Field(
        default="User logged out successfully",
        description="Human-readable status summary",
    )
