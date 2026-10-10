"""Smoke/structural test confirming the backend runs over HTTP/JSON.

This verifies the FastAPI application starts and responds, satisfying the
structural check that the Python + FastAPI backend runs separately
(Requirements 14.2, 14.5).
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
