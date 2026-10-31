"""Arogya AI — Cryptographic Token Issuance & Verification.

Module 7, Phase 7.2: Authentication & Protected Routes.
Generates and verifies JSON Web Tokens (JWT) using HMAC-SHA256 and configurable secrets.
"""

from datetime import datetime, timedelta, timezone
import uuid
import jwt


class TokenSecurityError(Exception):
    """Base exception for cryptographic token errors."""

    pass


class TokenExpiredError(TokenSecurityError):
    """Raised when an authentication token has expired."""

    pass


class TokenInvalidError(TokenSecurityError):
    """Raised when an authentication token signature or structure is invalid."""

    pass


def create_access_token(
    user_id: str | uuid.UUID,
    username: str,
    roles: list[str],
    secret_key: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Generate a signed JWT access token for an authenticated identity.

    Args:
        user_id: Unique UUID string identifier of user.
        username: Canonical user login handle.
        roles: List of active role names assigned to user.
        secret_key: Symmetric secret key string for HMAC-SHA256 signing.
        expires_delta: Optional custom lifetime duration; defaults to 60 minutes.

    Returns:
        Signed compact JWT token string.
    """
    now = datetime.now(timezone.utc)
    lifetime = expires_delta or timedelta(minutes=60)
    expire = now + lifetime

    payload = {
        "sub": str(user_id),
        "username": username,
        "roles": roles,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }

    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return token


def decode_access_token(token: str, secret_key: str) -> dict:
    """Decode and cryptographically verify a JWT access token.

    Args:
        token: Raw bearer token string.
        secret_key: Secret key string used for signature verification.

    Returns:
        Dictionary of claims contained in token payload.

    Raises:
        TokenExpiredError: If token has expired past its 'exp' claim.
        TokenInvalidError: If signature, algorithm, or payload is malformed.
    """
    if not token or not token.strip():
        raise TokenInvalidError("Authentication token is empty")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Authentication token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenInvalidError("Authentication token signature or format is invalid") from exc
