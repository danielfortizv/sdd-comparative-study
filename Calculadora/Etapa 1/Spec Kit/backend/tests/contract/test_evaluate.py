import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_evaluate_endpoint_success():
    payload = {"expression": "12.5 + 3 * (4 - 1.5) / 2"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["expression"] == "12.5 + 3 * (4 - 1.5) / 2"
    assert data["result"] == "16.25"

def test_evaluate_endpoint_scientific_radians():
    payload = {"expression": "sin(pi / 2)", "angle_unit": "radians"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "1"

def test_evaluate_endpoint_scientific_degrees():
    payload = {"expression": "sin(90)", "angle_unit": "degrees"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "1"

def test_evaluate_endpoint_division_by_zero():
    payload = {"expression": "5 / 0"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "DIVISION_BY_ZERO"
    assert "divide" in data["details"].lower()

def test_evaluate_endpoint_invalid_syntax():
    payload = {"expression": "2 + * 3"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "SYNTAX_ERROR"

def test_evaluate_endpoint_domain_error():
    payload = {"expression": "sqrt(-4)"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == "DOMAIN_ERROR"
