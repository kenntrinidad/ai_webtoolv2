"""User-account business logic, including the first Admin bootstrap flow."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import User
from app.services.password_service import hash_password

logger = logging.getLogger(__name__)


def bootstrap_initial_admin(db: Session, settings: Settings) -> User | None:
    """Create exactly one initial Admin when configured and none exists yet."""
    existing_admin_id = db.scalar(select(User.id).where(User.role == "admin").limit(1))
    if existing_admin_id is not None:
        return None

    username = (settings.initial_admin_username or "").strip()
    email = (settings.initial_admin_email or "").strip().lower()
    password = settings.initial_admin_password.get_secret_value() if settings.initial_admin_password else ""
    if not username or not email or not password:
        logger.warning("Initial Admin bootstrap skipped because configuration is incomplete")
        return None

    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password, rounds=settings.password_hash_rounds),
        role="admin",
        status="active",
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Initial Admin account created for username %s", username)
    return user
