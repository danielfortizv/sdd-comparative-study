import pytest
from decimal import Decimal
from src.core.evaluator import evaluate_expression
from src.api.v1.errors import CalculatorError

def test_decimal_precision():
    # 0.1 + 0.2 must be exactly 0.3 without binary representation errors
    assert evaluate_expression("0.1 + 0.2") == Decimal("0.3")
    assert evaluate_expression("0.1 * 0.2") == Decimal("0.02")

def test_pemdas_precedence():
    assert evaluate_expression("12.5 + 3 * (4 - 1.5) / 2") == Decimal("16.25")
    assert evaluate_expression("2 + 3 * 4") == Decimal("14")
    assert evaluate_expression("(2 + 3) * 4") == Decimal("20")

def test_division_by_zero():
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression("5 / 0")
    assert exc_info.value.error_code == "DIVISION_BY_ZERO"

def test_syntax_errors():
    invalid_expressions = [
        "1 + * 2",
        "(1 + 2",
        "1 + )",
        "abc",
        "1..2 + 3"
    ]
    for expr in invalid_expressions:
        with pytest.raises(CalculatorError) as exc_info:
            evaluate_expression(expr)
        assert exc_info.value.error_code == "SYNTAX_ERROR"

def test_scientific_constants():
    # pi and e
    assert abs(float(evaluate_expression("pi")) - 3.141592653589793) < 1e-15
    assert abs(float(evaluate_expression("e")) - 2.718281828459045) < 1e-15

def test_scientific_operations():
    # Powers and roots
    assert evaluate_expression("3 ^ 2") == Decimal("9")
    assert evaluate_expression("sqrt(16)") == Decimal("4")
    assert evaluate_expression("root(8, 3)") == Decimal("2")
    assert evaluate_expression("log10(100)") == Decimal("2")
    assert abs(float(evaluate_expression("ln(e)")) - 1.0) < 1e-15

def test_trigonometric_radians():
    # Trig in Radians (default)
    assert abs(float(evaluate_expression("sin(pi / 2)")) - 1.0) < 1e-15
    assert abs(float(evaluate_expression("cos(pi)")) - (-1.0)) < 1e-15
    assert abs(float(evaluate_expression("tan(0)")) - 0.0) < 1e-15

def test_trigonometric_degrees():
    # Trig in Degrees
    assert abs(float(evaluate_expression("sin(90)", angle_unit="degrees")) - 1.0) < 1e-15
    assert abs(float(evaluate_expression("cos(180)", angle_unit="degrees")) - (-1.0)) < 1e-15
    assert abs(float(evaluate_expression("tan(45)", angle_unit="degrees")) - 1.0) < 1e-15

def test_inverse_trigonometric():
    # Inverse trig in Radians and Degrees
    assert abs(float(evaluate_expression("asin(1)")) - 1.5707963267948966) < 1e-15  # pi / 2
    assert abs(float(evaluate_expression("asin(1)", angle_unit="degrees")) - 90.0) < 1e-15
    assert abs(float(evaluate_expression("acos(0)")) - 1.5707963267948966) < 1e-15  # pi / 2
    assert abs(float(evaluate_expression("acos(0)", angle_unit="degrees")) - 90.0) < 1e-15
    assert abs(float(evaluate_expression("atan(1)")) - 0.7853981633974483) < 1e-15  # pi / 4
    assert abs(float(evaluate_expression("atan(1)", angle_unit="degrees")) - 45.0) < 1e-15

def test_mathematical_domain_errors():
    # Sqrt of negative
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression("sqrt(-1)")
    assert exc_info.value.error_code == "DOMAIN_ERROR"
    
    # Log of negative
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression("ln(0)")
    assert exc_info.value.error_code == "DOMAIN_ERROR"
    
    # Inverse trig domain
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression("asin(2)")
    assert exc_info.value.error_code == "DOMAIN_ERROR"
    
    # Root domain (even root of negative)
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression("root(-8, 2)")
    assert exc_info.value.error_code == "DOMAIN_ERROR"

    # Fractional power of negative
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression("(-2) ^ 0.5")
    assert exc_info.value.error_code == "DOMAIN_ERROR"
