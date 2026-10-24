import pytest
from fastapi.testclient import TestClient
import sys
import os
import decimal

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
    assert evaluate_expression("3 + 4 * 2 - (1 + 1)") == 9
    assert evaluate_expression("(2 + 3) * 4") == 20
    assert evaluate_expression("2 + 3 * 4") == 14
    assert evaluate_expression("10 / (2 + 3) * 4") == 8
    assert evaluate_expression("2 * (3 + 4) / 2") == 7

def test_decimal_precision():
    res1 = evaluate_expression("0.1 + 0.2")
    assert str(res1) == "0.3"
    
    res2 = evaluate_expression("0.15 * 3")
    assert str(res2) == "0.45"
    
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
        evaluate_expression("3 + @")
        
    with pytest.raises(CalculatorError, match="Expression cannot be empty"):
        evaluate_expression("   ")

# ----------------------------------------------------
# Scientific Calculator Expansion Tests
# ----------------------------------------------------

def test_scientific_constants():
    assert evaluate_expression("pi") == decimal.Decimal("3.141592653589793238462643383")
    assert evaluate_expression("e") == decimal.Decimal("2.718281828459045235360287471")
    # Evaluating expressions with constants
    assert evaluate_expression("pi * 2") == decimal.Decimal("6.283185307179586476925286767")

def test_powers_and_roots():
    # Exponentiation (ast.Pow / **)
    assert evaluate_expression("2 ** 4") == 16
    assert evaluate_expression("5 ** 3") == 125
    # Square root
    assert evaluate_expression("sqrt(9)") == 3
    assert evaluate_expression("sqrt(2.25)") == 1.5
    # N-th root
    assert evaluate_expression("root(8, 3)") == 2
    assert evaluate_expression("root(625, 4)") == 5

def test_logarithms():
    # Natural Logarithm ln(e) = 1
    assert evaluate_expression("ln(e)") == 1
    # Base 10 Logarithm log10(100) = 2
    assert evaluate_expression("log10(100)") == 2

def test_trigonometry_radians():
    # Trigonometry in default Radians mode
    assert evaluate_expression("sin(0)") == 0
    assert evaluate_expression("cos(0)") == 1
    assert evaluate_expression("tan(0)") == 0
    
    # Rounded values due to floating-point representation in trigonometric formulas
    assert evaluate_expression("sin(pi / 2)") == 1
    assert evaluate_expression("cos(pi)") == -1
    assert evaluate_expression("tan(pi / 4)") == 1

def test_trigonometry_degrees():
    # Trigonometry in Degrees mode
    assert evaluate_expression("sin(90)", angle_unit="degrees") == 1
    assert evaluate_expression("cos(180)", angle_unit="degrees") == -1
    assert evaluate_expression("tan(45)", angle_unit="degrees") == 1
    assert evaluate_expression("asin(1)", angle_unit="degrees") == 90
    assert evaluate_expression("acos(0)", angle_unit="degrees") == 90
    assert evaluate_expression("atan(1)", angle_unit="degrees") == 45

def test_scientific_domain_errors():
    with pytest.raises(CalculatorError, match="Math domain error"):
        evaluate_expression("sqrt(-1)")
        
    with pytest.raises(CalculatorError, match="Math domain error"):
        evaluate_expression("ln(0)")
        
    with pytest.raises(CalculatorError, match="Math domain error"):
        evaluate_expression("log10(-5)")
        
    with pytest.raises(CalculatorError, match="Math domain error"):
        evaluate_expression("tan(90)", angle_unit="degrees")

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

def test_api_evaluate_scientific_degrees():
    response = client.post(
        "/api/v1/evaluate",
        json={
            "expression": "sin(90) + cos(180)",
            "angle_unit": "degrees"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["result"] == "0"

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
        json={"expression": "5 + #"}
    )
    assert response.status_code == 400
    data = response.json()
    assert "Invalid characters in expression" in data["detail"]
