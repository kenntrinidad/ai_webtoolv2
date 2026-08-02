"""Business logic for user CRUD operations and account lifecycle management."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.password_service import hash_password, validate_password


def list_users(db: Session) -> list[User]:
    return db.scalars(select(User).order_by(User.username)).all()


def get_user(db: Session, user_id: str) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, payload: UserCreate) -> User:
    validate_password(payload.password)
    user = User(
        username=payload.username.strip(),
        email=payload.email.strip().lower(),
        full_name=payload.full_name.strip() if payload.full_name else None,
        password_hash=hash_password(payload.password, rounds=12),
        role=payload.role,
        status=payload.status,
        must_change_password=payload.must_change_password if payload.must_change_password is not None else False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    if payload.username is not None:
        user.username = payload.username.strip()
    if payload.email is not None:
        user.email = payload.email.strip().lower()
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip() if payload.full_name else None
    if payload.password is not None:
        validate_password(payload.password)
        user.password_hash = hash_password(payload.password, rounds=12)
    if payload.role is not None:
        user.role = payload.role
    if payload.status is not None:
        user.status = payload.status
    if payload.must_change_password is not None:
        user.must_change_password = payload.must_change_password
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()
