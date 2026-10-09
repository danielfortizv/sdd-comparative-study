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
