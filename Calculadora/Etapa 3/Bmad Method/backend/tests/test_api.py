from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_api_success():
    payload = {"expression": "12.5 + 3 * (4 - 1.5) / 2"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert json_data["expression"] == payload["expression"]
    assert json_data["result"] == "16.25"

def test_api_division_by_zero():
    payload = {"expression": "10 / 0"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["status"] == "error"
    assert json_data["error_type"] == "division_by_zero"
    assert json_data["message"] == "Error: Division by zero"

def test_api_unbalanced_parentheses():
    payload = {"expression": "(10 + 5"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["status"] == "error"
    assert json_data["error_type"] == "unbalanced_parentheses"
    assert json_data["message"] == "Error: Unbalanced parentheses"

def test_api_empty_expression():
    payload = {"expression": "   "}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["status"] == "error"
    assert json_data["error_type"] == "empty_expression"
    assert json_data["message"] == "Error: Expression is empty"

def test_api_validation_error():
    # Pass a non-string list instead of a string
    payload = {"expression": []}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["status"] == "error"
    assert json_data["error_type"] == "request_validation_error"
    assert "Error:" in json_data["message"]

def test_api_health_check():
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert json_data["service"] == "calculator-api"


def test_api_scientific_radians():
    payload = {"expression": "sin(pi / 2)", "angle_unit": "radians"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert abs(float(json_data["result"]) - 1.0) < 1e-10


def test_api_scientific_degrees():
    payload = {"expression": "sin(90)", "angle_unit": "degrees"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "success"
    assert abs(float(json_data["result"]) - 1.0) < 1e-10


def test_api_scientific_domain_error():
    payload = {"expression": "sqrt(-4)"}
    response = client.post("/api/v1/evaluate", json=payload)
    assert response.status_code == 422
    json_data = response.json()
    assert json_data["status"] == "error"
    assert "Square root of a negative number" in json_data["message"]

