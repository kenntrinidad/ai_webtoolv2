"""Credential verification and local login-attempt protection."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import User
from app.services.password_service import hash_password, verify_password


class AuthenticationError(ValueError):
    """Raised when supplied credentials are not valid for an active user."""


class LoginRateLimitError(ValueError):
    """Raised when a client has exceeded the temporary login failure limit."""


class LoginAttemptLimiter:
    """Small in-memory limiter suitable for local development deployments."""

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._locked_until: dict[str, float] = {}

    def check(self, client_key: str, *, window_seconds: int) -> None:
        now = time.monotonic()
        if self._locked_until.get(client_key, 0) > now:
            raise LoginRateLimitError
        self._locked_until.pop(client_key, None)
        failures = self._failures[client_key]
        while failures and now - failures[0] > window_seconds:
            failures.popleft()

    def record_failure(
        self, client_key: str, *, max_attempts: int, window_seconds: int, lockout_seconds: int
    ) -> None:
        now = time.monotonic()
        failures = self._failures[client_key]
        while failures and now - failures[0] > window_seconds:
            failures.popleft()
        failures.append(now)
        if len(failures) >= max_attempts:
            self._locked_until[client_key] = now + lockout_seconds
            failures.clear()

    def record_success(self, client_key: str) -> None:
        self._failures.pop(client_key, None)
        self._locked_until.pop(client_key, None)


login_attempt_limiter = LoginAttemptLimiter()


def authenticate_user(db: Session, *, identifier: str, password: str) -> User:
    """Return an active user only when their credentials are valid."""
    normalized_identifier = identifier.strip()
    user = db.scalar(
        select(User).where(
            or_(User.username == normalized_identifier, User.email == normalized_identifier.lower())
        )
    )
    if user is None or user.status != "active" or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid username/email or password.")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session, *, user: User, current_password: str, new_password: str, rounds: int
) -> User:
    """Verify the current password and persist a policy-compliant replacement."""
    if not verify_password(current_password, user.password_hash):
        raise AuthenticationError("Current password is incorrect.")
    if verify_password(new_password, user.password_hash):
        raise AuthenticationError("New password must be different from the current password.")

    user.password_hash = hash_password(new_password, rounds=rounds)
    user.must_change_password = False
    db.commit()
    db.refresh(user)
    return user
