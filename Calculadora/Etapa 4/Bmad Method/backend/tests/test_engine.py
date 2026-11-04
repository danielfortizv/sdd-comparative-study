import pytest
from decimal import Decimal
from backend.app.engine.parser import safe_parse_and_evaluate, MathEvaluationError

def test_basic_arithmetic():
    assert safe_parse_and_evaluate("10 + 5") == 15
    assert safe_parse_and_evaluate("20 - 4") == 16
    assert safe_parse_and_evaluate("3 * 8") == 24
    assert safe_parse_and_evaluate("15 / 3") == 5

def test_pemdas_precedence():
    assert safe_parse_and_evaluate("10 + 2 * 5") == 20
    assert safe_parse_and_evaluate("(10 + 2) * 5") == 60
    assert safe_parse_and_evaluate("12.5 + 3 * (4 - 1.5) / 2") == 16.25

def test_unary_operations():
    assert safe_parse_and_evaluate("-5") == -5
    assert safe_parse_and_evaluate("+3") == 3
    assert safe_parse_and_evaluate("-(10 + 5)") == -15

def test_decimal_precision():
    result = safe_parse_and_evaluate("0.1 + 0.2")
    assert isinstance(result, Decimal)
    assert result == Decimal("0.3")
    assert str(result) == "0.3"

    result2 = safe_parse_and_evaluate("1.0 - 0.9")
    assert result2 == Decimal("0.1")
    assert str(result2) == "0.1"

def test_division_by_zero():
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("10 / 0")
    assert str(exc.value) == "Error: Division by zero"

    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("5 / (2 - 2)")
    assert str(exc.value) == "Error: Division by zero"

def test_unbalanced_parentheses():
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("(10 + 5")
    assert str(exc.value) == "Error: Unbalanced parentheses"

    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("10 + 5)")
    assert str(exc.value) == "Error: Unbalanced parentheses"

def test_invalid_syntax():
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("12 + * 3")
    assert str(exc.value) == "Error: Invalid syntax structure"

def test_empty_and_whitespace():
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("")
    assert str(exc.value) == "Error: Expression is empty"

    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("   ")
    assert str(exc.value) == "Error: Expression is empty"

def test_dangerous_injection_rejection():
    # Attempt RCE, calling standard built-in functions, or assignments
    dangerous_expressions = [
        "__import__('os').system('ls')",
        "eval('1+1')",
        "print('hello')",
        "abs(-10)",
        "pow(2, 3)",
        "x = 10",
        "lambda: 5"
    ]
    for expr in dangerous_expressions:
        with pytest.raises(MathEvaluationError) as exc:
            safe_parse_and_evaluate(expr)
        assert str(exc.value).startswith("Error:")

def test_boolean_rejection():
    for expr in ["True", "False", "True + 1"]:
        with pytest.raises(MathEvaluationError) as exc:
            safe_parse_and_evaluate(expr)
        assert str(exc.value).startswith("Error:")

def test_non_string_rejection():
    for val in [None, 123, 45.67, [], {}]:
        with pytest.raises(MathEvaluationError) as exc:
            safe_parse_and_evaluate(val)
        assert str(exc.value) == "Error: Input expression must be a string"


def test_scientific_constants():
    # pi and e values should evaluate correctly
    assert abs(safe_parse_and_evaluate("pi") - Decimal("3.141592653589793238462643383")) < Decimal("1e-15")
    assert abs(safe_parse_and_evaluate("e") - Decimal("2.718281828459045235360287471")) < Decimal("1e-15")
    # Expression containing constants should parse correctly
    assert safe_parse_and_evaluate("2 * pi") > 6.28


def test_scientific_trig_radians():
    # In radians: sin(pi / 2) == 1, cos(pi) == -1, tan(0) == 0
    assert abs(safe_parse_and_evaluate("sin(pi / 2)", angle_unit="radians") - 1) < Decimal("1e-10")
    assert abs(safe_parse_and_evaluate("cos(pi)", angle_unit="radians") - (-1)) < Decimal("1e-10")
    assert abs(safe_parse_and_evaluate("tan(0)", angle_unit="radians")) < Decimal("1e-10")


def test_scientific_trig_degrees():
    # In degrees: sin(90) == 1, cos(180) == -1, tan(45) == 1
    assert abs(safe_parse_and_evaluate("sin(90)", angle_unit="degrees") - 1) < Decimal("1e-10")
    assert abs(safe_parse_and_evaluate("cos(180)", angle_unit="degrees") - (-1)) < Decimal("1e-10")
    assert abs(safe_parse_and_evaluate("tan(45)", angle_unit="degrees") - 1) < Decimal("1e-10")


def test_scientific_inverse_trig():
    # asin(1) in degrees should be 90, acos(0) should be 90, atan(1) should be 45
    assert abs(safe_parse_and_evaluate("asin(1)", angle_unit="degrees") - 90) < Decimal("1e-10")
    assert abs(safe_parse_and_evaluate("acos(0)", angle_unit="degrees") - 90) < Decimal("1e-10")
    assert abs(safe_parse_and_evaluate("atan(1)", angle_unit="degrees") - 45) < Decimal("1e-10")

    # In radians
    assert abs(safe_parse_and_evaluate("asin(1)", angle_unit="radians") - safe_parse_and_evaluate("pi / 2")) < Decimal("1e-10")


def test_scientific_exponents_and_roots():
    # Exponentiation and roots
    assert safe_parse_and_evaluate("2 ** 10") == 1024
    assert safe_parse_and_evaluate("sqrt(16)") == 4
    # Fractional exponent for negative number must throw error
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("(-4) ** 0.5")
    assert "Fractional power of a negative number is undefined" in str(exc.value)


def test_scientific_logarithms():
    assert abs(safe_parse_and_evaluate("ln(e)") - 1) < Decimal("1e-15")
    assert safe_parse_and_evaluate("log10(100)") == 2
    assert safe_parse_and_evaluate("log(1000)") == 3


def test_scientific_domain_errors():
    # sqrt(<0)
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("sqrt(-9)")
    assert "Square root of a negative number is undefined" in str(exc.value)

    # log(<=0)
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("ln(0)")
    assert "Logarithm of zero or a negative number is undefined" in str(exc.value)

    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("log(-10)")
    assert "Logarithm of zero or a negative number is undefined" in str(exc.value)

    # asin out of range
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("asin(1.5)")
    assert "Inverse trigonometric function domain is [-1, 1]" in str(exc.value)

    # tan(90 deg) vertical asymptote
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("tan(90)", angle_unit="degrees")
    assert "Tangent undefined at this angle" in str(exc.value)

    # 0 ** -1 division by zero
    with pytest.raises(MathEvaluationError) as exc:
        safe_parse_and_evaluate("0 ** -1")
    assert "Division by zero in power operation" in str(exc.value)

