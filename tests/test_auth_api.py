from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app
from app.models import User
from app.services.password_service import hash_password


def test_login_logout_and_protected_routes() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as db:
        db.add(
            User(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("SecurePassword1", rounds=10),
                role="admin",
            )
        )
        db.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        assert client.get("/api/agents").status_code == 401
        invalid = client.post("/api/auth/login", json={"identifier": "admin", "password": "WrongPassword1"})
        assert invalid.status_code == 401
        assert invalid.json()["detail"] == "Invalid username/email or password."

        logged_in = client.post(
            "/api/auth/login", json={"identifier": "admin@example.com", "password": "SecurePassword1"}
        )
        assert logged_in.status_code == 200
        assert logged_in.json()["username"] == "admin"
        assert "httponly" in logged_in.headers["set-cookie"].lower()

        assert client.get("/api/auth/me").status_code == 200
        assert client.get("/api/agents").status_code == 200
        assert client.post("/api/auth/logout").status_code == 204
        assert client.get("/api/agents").status_code == 401

    app.dependency_overrides.clear()


def test_required_password_change_blocks_business_apis_until_completed() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    with testing_session() as db:
        db.add(
            User(
                username="new-user",
                email="new-user@example.com",
                password_hash=hash_password("TemporaryPass1", rounds=10),
                must_change_password=True,
            )
        )
        db.commit()

    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        assert client.post(
            "/api/auth/login", json={"identifier": "new-user", "password": "TemporaryPass1"}
        ).status_code == 200
        assert client.get("/api/auth/me").json()["must_change_password"] is True
        assert client.get("/api/agents").status_code == 403
        assert client.post(
            "/api/auth/change-password",
            json={"current_password": "not-the-password", "new_password": "ReplacementPass1"},
        ).status_code == 400
        changed = client.post(
            "/api/auth/change-password",
            json={"current_password": "TemporaryPass1", "new_password": "ReplacementPass1"},
        )
        assert changed.status_code == 200
        assert changed.json()["must_change_password"] is False
        assert client.get("/api/agents").status_code == 200

    app.dependency_overrides.clear()
