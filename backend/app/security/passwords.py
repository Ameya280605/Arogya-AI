"""Arogya AI — Cryptographic Password Hashing & Verification.

Module 7, Phase 7.2: Authentication & Protected Routes.
Implements secure password hashing using bcrypt with adaptive salt generation.
Plaintext passwords or weak hashing algorithms are strictly prohibited.
"""

import logging
import bcrypt

logger = logging.getLogger("arogya.security.passwords")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with standard work factor.

    Args:
        plain_password: Clean plaintext password string.

    Returns:
        Hashed password string (formatted with bcrypt prefix and salt).

    Raises:
        ValueError: If password is empty or invalid.
    """
    if not plain_password or not plain_password.strip():
        raise ValueError("Password cannot be empty or whitespace only")

    # Bcrypt truncates passwords over 72 bytes; enforce length guard
    password_bytes = plain_password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password exceeds maximum bcrypt length of 72 bytes")

    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a candidate password against stored cryptographic hash.

    Args:
        plain_password: Password to verify.
        hashed_password: Stored bcrypt hash string, or None/locked marker.

    Returns:
        True if password matches hash; False otherwise (fail safely).
    """
    if not plain_password or not hashed_password:
        return False

    # Check for locked/disabled synthetic account sentinels
    if hashed_password.startswith("!"):
        return False

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception as exc:
        logger.warning("Password verification failed unexpectedly: %s", type(exc).__name__)
        return False
