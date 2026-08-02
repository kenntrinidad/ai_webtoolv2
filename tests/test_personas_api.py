from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app
from tests.auth_helpers import allow_authenticated_requests


def test_persona_crud_api() -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
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
        created = client.post(
            "/api/personas",
            json={
                "name": "Professional Support",
                "description": "Customer support personality",
                "system_prompt": "Answer clearly and politely.",
            },
        )
        assert created.status_code == 201
        persona_id = created.json()["id"]

        listed = client.get("/api/personas")
        assert listed.status_code == 200
        assert [persona["id"] for persona in listed.json()] == [persona_id]

        updated = client.put(
            f"/api/personas/{persona_id}", json={"system_prompt": "Use verified knowledge."}
        )
        assert updated.status_code == 200
        assert updated.json()["system_prompt"] == "Use verified knowledge."

        assert client.delete(f"/api/personas/{persona_id}").status_code == 204
        assert client.get(f"/api/personas/{persona_id}").status_code == 404

    app.dependency_overrides.clear()
