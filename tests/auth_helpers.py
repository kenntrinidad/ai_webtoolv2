"""Helpers for testing APIs protected by the Phase B session dependency."""

from fastapi import FastAPI

from app.core.auth import require_authenticated_user
from app.models import User


def allow_authenticated_requests(app: FastAPI) -> None:
    """Override route authentication where a test focuses on another concern."""
    app.dependency_overrides[require_authenticated_user] = lambda: User(
        id="test-user", username="tester", email="tester@example.com", password_hash="not-used", role="admin"
    )
