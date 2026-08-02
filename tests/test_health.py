from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_reports_running_application() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_root_page_is_available_in_a_browser() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "Agent Builder" in response.text
    assert "AI OPERATIONS" in response.text
    assert "Agent Testing Playground" in response.text
