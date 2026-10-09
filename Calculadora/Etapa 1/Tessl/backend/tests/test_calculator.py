import pytest
from decimal import Decimal
from app.calculator import evaluate_expression

def test_basic_arithmetic():
    assert evaluate_expression("2+3") == Decimal("5")
    assert evaluate_expression("10 - 4") == Decimal("6")
    assert evaluate_expression("4 * 5") == Decimal("20")
    assert evaluate_expression("20 / 4") == Decimal("5")

def test_pemdas_precedence():
    # Multiplication before addition
    assert evaluate_expression("2 + 3 * 4") == Decimal("14")
    # Division before subtraction
    assert evaluate_expression("10 - 6 / 2") == Decimal("7")
    # Parentheses first
    assert evaluate_expression("(2 + 3) * 4") == Decimal("20")
    # Chained complex expression
    # 12.5 + 3 * (4 - 1.5) / 2 = 12.5 + 3 * 2.5 / 2 = 12.5 + 7.5 / 2 = 12.5 + 3.75 = 16.25
    assert evaluate_expression("12.5 + 3 * (4 - 1.5) / 2") == Decimal("16.25")

def test_decimal_precision():
    # Standard floating point issue: 0.1 + 0.2 = 0.30000000000000004
    # High-precision Decimal should evaluate it strictly to 0.3
    assert evaluate_expression("0.1 + 0.2") == Decimal("0.3")
    assert evaluate_expression("1.000000001 - 0.000000001") == Decimal("1")
    assert evaluate_expression("1 / 3") == Decimal("1") / Decimal("3")

def test_unary_operators():
    assert evaluate_expression("-5") == Decimal("-5")
    assert evaluate_expression("+5") == Decimal("5")
    assert evaluate_expression("3 + -5") == Decimal("-2")
    assert evaluate_expression("3 * -5") == Decimal("-15")
    assert evaluate_expression("-(3 + 5)") == Decimal("-8")
    assert evaluate_expression("-3 * -(5 - 2)") == Decimal("9")

def test_whitespace_handling():
    assert evaluate_expression("  12.5   +   3  *  ( 4  -  1.5 ) / 2 ") == Decimal("16.25")

def test_division_by_zero():
    with pytest.raises(ZeroDivisionError, match="Division by zero"):
        evaluate_expression("5 / 0")
    with pytest.raises(ZeroDivisionError, match="Division by zero"):
        evaluate_expression("10 / (5 - 5)")

def test_syntax_errors():
    with pytest.raises(ValueError, match="Expected number or '\\('"):
        evaluate_expression("12 + * 3")
    with pytest.raises(ValueError, match="Expected '\\)'"):
        evaluate_expression("(1 + 2")
    with pytest.raises(ValueError, match="Unexpected token"):
        evaluate_expression("1 2")
    with pytest.raises(ValueError, match="invalid characters"):
        evaluate_expression("3 + x")
    with pytest.raises(ValueError, match="Expression is empty"):
        evaluate_expression("   ")
