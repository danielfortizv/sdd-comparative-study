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
    assert evaluate_expression("12.5 + 3 * (4 - 1.5) / 2") == Decimal("16.25")

def test_decimal_precision():
    # Standard floating point issue: 0.1 + 0.2 = 0.30000000000000004
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
    with pytest.raises(ValueError, match="Expected number"):
        evaluate_expression("12 + * 3")
    with pytest.raises(ValueError, match="Expected '\\)'"):
        evaluate_expression("(1 + 2")
    with pytest.raises(ValueError, match="Unexpected token"):
        evaluate_expression("1 2")
    with pytest.raises(ValueError, match="Expected number, constant, function"):
        evaluate_expression("3 + x")
    with pytest.raises(ValueError, match="invalid characters"):
        evaluate_expression("3 + @")
    with pytest.raises(ValueError, match="Expression is empty"):
        evaluate_expression("   ")

# ==========================================
# STAGE 2 SCIENTIFIC CALCULATOR TESTS
# ==========================================

def test_scientific_constants():
    # pi and e constants
    assert evaluate_expression("pi") == Decimal("3.141592653589793238462643383")
    assert evaluate_expression("e") == Decimal("2.718281828459045235360287471")
    assert evaluate_expression("2 * pi") == Decimal("2") * Decimal("3.141592653589793238462643383")

def test_exponentiation():
    # Exponentiation ^ operator
    assert evaluate_expression("2^3") == Decimal("8")
    assert evaluate_expression("10^2") == Decimal("100")
    # Precedence: unary lower than exponentiation (so -2^2 = -4, (-2)^2 = 4)
    assert evaluate_expression("-2^2") == Decimal("-4")
    assert evaluate_expression("(-2)^2") == Decimal("4")
    # Fractional exponent (e.g. 9^0.5 = 3)
    assert pytest.approx(float(evaluate_expression("9^0.5"))) == 3.0

def test_square_root():
    assert evaluate_expression("sqrt(9)") == Decimal("3")
    assert evaluate_expression("sqrt(2.25)") == Decimal("1.5")
    with pytest.raises(ValueError, match="Square root of negative number"):
        evaluate_expression("sqrt(-1)")

def test_logarithms():
    # Natural log ln
    assert pytest.approx(float(evaluate_expression("ln(e)"))) == 1.0
    # Base-10 log
    assert evaluate_expression("log(100)") == Decimal("2")
    
    with pytest.raises(ValueError, match="Logarithm of non-positive number"):
        evaluate_expression("ln(0)")
    with pytest.raises(ValueError, match="Logarithm of non-positive number"):
        evaluate_expression("log(-5)")

def test_trig_functions_radians():
    # sin, cos, tan in radians mode (default)
    assert pytest.approx(float(evaluate_expression("sin(pi / 2)", "radians"))) == 1.0
    assert pytest.approx(float(evaluate_expression("cos(pi)", "radians"))) == -1.0
    assert pytest.approx(float(evaluate_expression("tan(0)", "radians"))) == 0.0

def test_trig_functions_degrees():
    # sin, cos, tan in degrees mode
    assert pytest.approx(float(evaluate_expression("sin(90)", "degrees"))) == 1.0
    assert pytest.approx(float(evaluate_expression("cos(180)", "degrees"))) == -1.0
    assert pytest.approx(float(evaluate_expression("tan(45)", "degrees"))) == 1.0

def test_inverse_trig_functions():
    # asin, acos, atan
    assert pytest.approx(float(evaluate_expression("asin(1)", "radians"))) == float(Decimal("3.141592653589793238462643383") / Decimal("2"))
    assert pytest.approx(float(evaluate_expression("acos(1)", "radians"))) == 0.0
    assert pytest.approx(float(evaluate_expression("atan(1)", "radians"))) == float(Decimal("3.141592653589793238462643383") / Decimal("4"))
    
    # degrees mode
    assert pytest.approx(float(evaluate_expression("asin(0.5)", "degrees"))) == 30.0
    assert pytest.approx(float(evaluate_expression("acos(0.5)", "degrees"))) == 60.0
    
    with pytest.raises(ValueError, match="asin input must be between -1 and 1"):
        evaluate_expression("asin(2)")
