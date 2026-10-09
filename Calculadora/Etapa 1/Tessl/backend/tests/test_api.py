from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_evaluate_endpoint_success():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "12.5 + 3 * (4 - 1.5) / 2"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": 16.25}

def test_evaluate_endpoint_decimal_precision():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "0.1 + 0.2"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": 0.3}

def test_evaluate_endpoint_division_by_zero():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "5 / 0"}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "math error"
    assert "Division by zero" in detail["message"]

def test_evaluate_endpoint_syntax_error():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "12 + * 3"}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "syntax error"
    assert "Expected number" in detail["message"]

def test_evaluate_endpoint_empty_expression():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "   "}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "syntax error"
    assert "Expression is empty" in detail["message"]
