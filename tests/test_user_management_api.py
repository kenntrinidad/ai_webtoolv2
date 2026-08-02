from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app
from app.models import User
from app.services.password_service import hash_password
from tests.auth_helpers import allow_authenticated_requests


def test_user_crud_requires_admin() -> None:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    app = create_app()
    allow_authenticated_requests(app)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        response = client.post(
            "/api/users",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePassword1",
                "role": "user",
                "status": "active",
            },
        )
        assert response.status_code == 201
        assert response.json()["username"] == "newuser"

        user_id = response.json()["id"]
        list_response = client.get("/api/users")
        assert list_response.status_code == 200
        assert any(user["id"] == user_id for user in list_response.json())

        updated = client.put(f"/api/users/{user_id}", json={"status": "inactive"})
        assert updated.json()["status"] == "inactive"

        deleted = client.delete(f"/api/users/{user_id}")
        assert deleted.status_code == 204

    app.dependency_overrides.clear()
