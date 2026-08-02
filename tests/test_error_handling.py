from fastapi.testclient import TestClient

from app.main import create_app
from tests.auth_helpers import allow_authenticated_requests


def test_validation_errors_are_structured_and_safe() -> None:
    app = create_app()
    allow_authenticated_requests(app)
    with TestClient(app) as client:
        response = client.post("/api/personas", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Invalid request data"
    assert {item["field"] for item in body["errors"]} >= {"body.name", "body.system_prompt"}


def test_unexpected_errors_do_not_expose_stack_traces() -> None:
    app = create_app()

    @app.get("/test-error", include_in_schema=False)
    def trigger_error() -> None:
        raise RuntimeError("sensitive internal failure")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-error")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "sensitive internal failure" not in response.text
