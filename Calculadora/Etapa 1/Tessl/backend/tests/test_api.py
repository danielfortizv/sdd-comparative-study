from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_evaluate_endpoint_success():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "12.5 + 3 * (4 - 1.5) / 2", "angle_unit": "radians"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": 16.25}

def test_evaluate_endpoint_decimal_precision():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "0.1 + 0.2", "angle_unit": "radians"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": 0.3}

def test_evaluate_endpoint_division_by_zero():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "5 / 0", "angle_unit": "radians"}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "math error"
    assert "Division by zero" in detail["message"]

def test_evaluate_endpoint_syntax_error():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "12 + * 3", "angle_unit": "radians"}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "syntax error"
    assert "Expected number" in detail["message"]

def test_evaluate_endpoint_empty_expression():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "   ", "angle_unit": "radians"}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "syntax error"
    assert "Expression is empty" in detail["message"]

# ==========================================
# STAGE 2 API SCIENTIFIC TESTS
# ==========================================

def test_evaluate_endpoint_trig_radians():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "sin(pi / 2)", "angle_unit": "radians"}
    )
    assert response.status_code == 200
    assert response.json()["result"] == 1.0

def test_evaluate_endpoint_trig_degrees():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "sin(90)", "angle_unit": "degrees"}
    )
    assert response.status_code == 200
    assert response.json()["result"] == 1.0

def test_evaluate_endpoint_exponentiation():
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "-2^2", "angle_unit": "radians"}
    )
    assert response.status_code == 200
    assert response.json() == {"result": -4.0}

def test_evaluate_endpoint_math_domain_errors():
    # Square root of negative number
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "sqrt(-9)", "angle_unit": "radians"}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "syntax error"
    assert "Square root of negative number" in detail["message"]

    # Logarithm of negative number
    response = client.post(
        "/api/v1/evaluate",
        json={"operation": "log(-1)", "angle_unit": "radians"}
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["type"] == "syntax error"
    assert "Logarithm of non-positive number" in detail["message"]
