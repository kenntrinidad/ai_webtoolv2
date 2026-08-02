from fastapi.testclient import TestClient

from app.main import create_app


def test_application_responses_include_security_headers() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/api/health")

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["content-security-policy"].startswith("default-src 'self'")
