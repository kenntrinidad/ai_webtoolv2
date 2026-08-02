import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import Base
from app.models import User
from app.services.password_service import hash_password, verify_password
from app.services.user_service import bootstrap_initial_admin


def test_passwords_are_bcrypt_hashed_and_verifiable() -> None:
    password_hash = hash_password("SecurePassword1", rounds=10)

    assert password_hash != "SecurePassword1"
    assert password_hash.startswith("$2")
    assert verify_password("SecurePassword1", password_hash)
    assert not verify_password("WrongPassword1", password_hash)


def test_initial_admin_bootstrap_runs_once() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    settings = Settings(
        initial_admin_username="administrator",
        initial_admin_email="admin@example.com",
        initial_admin_password="SecurePassword1",
        password_hash_rounds=10,
    )

    with Session(engine) as db:
        created = bootstrap_initial_admin(db, settings)
        second_attempt = bootstrap_initial_admin(db, settings)
        admins = list(db.query(User).filter_by(role="admin"))

    assert created is not None
    assert created.username == "administrator"
    assert created.password_hash != "SecurePassword1"
    assert verify_password("SecurePassword1", created.password_hash)
    assert second_attempt is None
    assert len(admins) == 1


def test_initial_admin_bootstrap_requires_password_change() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    settings = Settings(
        initial_admin_username="administrator",
        initial_admin_email="admin@example.com",
        initial_admin_password="SecurePassword1",
        password_hash_rounds=10,
    )

    with Session(engine) as db:
        created = bootstrap_initial_admin(db, settings)

    assert created is not None
    assert created.must_change_password is True


def test_initial_admin_bootstrap_skips_incomplete_configuration() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        created = bootstrap_initial_admin(
            db,
            Settings(
                initial_admin_username="",
                initial_admin_email="",
                initial_admin_password="",
            ),
        )
        assert db.query(User).count() == 0

    assert created is None
