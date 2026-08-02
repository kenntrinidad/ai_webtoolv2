from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.core.database import Base, get_db
from app.main import create_app
from app.services import document_service
from tests.auth_helpers import allow_authenticated_requests


def test_document_upload_list_delete_and_validation(tmp_path, monkeypatch) -> None:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(
        document_service, "get_settings", lambda: Settings(document_storage_path=tmp_path)
    )
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
        agent = client.post("/api/agents", json={"name": "Knowledge Agent"})
        agent_id = agent.json()["id"]

        uploaded = client.post(
            f"/api/agents/{agent_id}/documents",
            files={"file": ("../../company policy.txt", b"Returns are accepted within 30 days.", "text/plain")},
        )
        assert uploaded.status_code == 201
        document = uploaded.json()
        assert document["original_filename"] == "company_policy.txt"
        assert document["file_type"] == "txt"

        duplicate = client.post(
            f"/api/agents/{agent_id}/documents",
            files={"file": ("copy.txt", b"Returns are accepted within 30 days.", "text/plain")},
        )
        assert duplicate.status_code == 409
        assert client.get(f"/api/agents/{agent_id}/documents").json()[0]["id"] == document["id"]
        assert client.delete(f"/api/agents/{agent_id}/documents/{document['id']}").status_code == 204
        assert not list(tmp_path.rglob("*.txt"))

        invalid = client.post(
            f"/api/agents/{agent_id}/documents",
            files={"file": ("malware.exe", b"not allowed", "application/octet-stream")},
        )
        assert invalid.status_code == 422

    app.dependency_overrides.clear()
