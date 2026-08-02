"""Password hashing and verification, isolated from user-management workflows."""

import bcrypt


class PasswordPolicyError(ValueError):
    """Raised when a supplied password does not meet the baseline policy."""


def validate_password(password: str) -> None:
    """Require a baseline suitable for bootstrap and future user credentials."""
    if len(password) < 12:
        raise PasswordPolicyError("Password must be at least 12 characters long")
    if not any(character.islower() for character in password):
        raise PasswordPolicyError("Password must contain a lowercase letter")
    if not any(character.isupper() for character in password):
        raise PasswordPolicyError("Password must contain an uppercase letter")
    if not any(character.isdigit() for character in password):
        raise PasswordPolicyError("Password must contain a number")


def hash_password(password: str, *, rounds: int) -> str:
    """Validate and hash a password using bcrypt with a configurable cost factor."""
    validate_password(password)
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=rounds)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Safely compare a candidate password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        return False
