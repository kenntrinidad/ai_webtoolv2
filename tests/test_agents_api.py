from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import create_app
from tests.auth_helpers import allow_authenticated_requests


def test_agent_crud_and_persona_assignment_api() -> None:
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
        persona = client.post(
            "/api/personas", json={"name": "Support", "system_prompt": "Be helpful."}
        )
        persona_id = persona.json()["id"]

        created = client.post(
            "/api/agents",
            json={
                "name": "Customer Support Agent",
                "nickname": "JARVIS",
                "description": "Handles customer questions.",
                "persona_id": persona_id,
            },
        )
        assert created.status_code == 201
        agent_id = created.json()["id"]
        assert created.json()["persona_id"] == persona_id
        assert created.json()["status"] == "active"

        updated = client.put(
            f"/api/agents/{agent_id}", json={"status": "inactive", "persona_id": None}
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "inactive"
        assert updated.json()["persona_id"] is None

        assert client.get("/api/agents").json()[0]["id"] == agent_id
        assert client.delete(f"/api/agents/{agent_id}").status_code == 204
        assert client.get(f"/api/agents/{agent_id}").status_code == 404

    app.dependency_overrides.clear()
