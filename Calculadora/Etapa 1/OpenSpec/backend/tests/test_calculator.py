import pytest
from fastapi.testclient import TestClient
import sys
import os

# Ensure the app is importable from the backend root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.calculator import evaluate_expression, CalculatorError
from app.main import app

client = TestClient(app)

# ----------------------------------------------------
# Core Math Engine Tests
# ----------------------------------------------------

def test_basic_arithmetic():
    assert evaluate_expression("5 + 3") == 8
    assert evaluate_expression("10 - 4.5") == 5.5
    assert evaluate_expression("4 * 2.5") == 10
    assert evaluate_expression("9 / 2") == 4.5

def test_pemdas_precedence():
    # 3 + 4 * 2 - (1 + 1) -> 3 + 8 - 2 -> 9
    assert evaluate_expression("3 + 4 * 2 - (1 + 1)") == 9
    # (2 + 3) * 4 -> 20
    assert evaluate_expression("(2 + 3) * 4") == 20
    # 2 + 3 * 4 -> 14
    assert evaluate_expression("2 + 3 * 4") == 14
    # 10 / (2 + 3) * 4 -> 5 * 4 -> 8 ? No: 10 / 5 * 4 = 2 * 4 = 8
    assert evaluate_expression("10 / (2 + 3) * 4") == 8
    # 2 * (3 + 4) / 2 -> 14 / 2 -> 7
    assert evaluate_expression("2 * (3 + 4) / 2") == 7

def test_decimal_precision():
    # Standard float error: 0.1 + 0.2 is 0.30000000000000004
    # Our engine should return exactly 0.3
    res1 = evaluate_expression("0.1 + 0.2")
    assert str(res1) == "0.3"
    
    # 0.15 * 3 should be 0.45 exactly
    res2 = evaluate_expression("0.15 * 3")
    assert str(res2) == "0.45"
    
    # 1 / 3 should have 28 decimal places
    res3 = evaluate_expression("1 / 3")
    assert str(res3).startswith("0.33333333333")

def test_error_handling():
    with pytest.raises(CalculatorError, match="Division by zero"):
        evaluate_expression("5 / 0")
        
    with pytest.raises(CalculatorError, match="Malformed expression or mismatched parentheses"):
        evaluate_expression("(3 + 2")
        
    with pytest.raises(CalculatorError, match="Malformed expression or mismatched parentheses"):
        evaluate_expression("3 + * 2")
        
    with pytest.raises(CalculatorError, match="Invalid characters in expression"):
        evaluate_expression("3 + x")
        
    with pytest.raises(CalculatorError, match="Expression cannot be empty"):
        evaluate_expression("   ")

# ----------------------------------------------------
# API Endpoint Tests
# ----------------------------------------------------

def test_api_evaluate_success():
    response = client.post(
        "/api/v1/evaluate",
        json={"expression": "12.5 + 3 * (4 - 1.5) / 2"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["expression"] == "12.5 + 3 * (4 - 1.5) / 2"
    assert data["result"] == "16.25"

def test_api_evaluate_division_by_zero():
    response = client.post(
        "/api/v1/evaluate",
        json={"expression": "10 / (2 - 2)"}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Division by zero" in data["detail"]

def test_api_evaluate_mismatched_parentheses():
    response = client.post(
        "/api/v1/evaluate",
        json={"expression": "(5 + 5"}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Malformed expression or mismatched parentheses" in data["detail"]

def test_api_evaluate_invalid_characters():
    response = client.post(
        "/api/v1/evaluate",
        json={"expression": "5 + abc"}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid characters in expression" in data["detail"]
