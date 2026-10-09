import pytest
from decimal import Decimal
from src.core.evaluator import evaluate_expression
from src.api.v1.errors import CalculatorError

def test_decimal_precision():
    # 0.1 + 0.2 must be exactly 0.3 without binary representation errors
    assert evaluate_expression("0.1 + 0.2") == Decimal("0.3")
    assert evaluate_expression("0.1 * 0.2") == Decimal("0.02")

def test_pemdas_precedence():
    # 12.5 + 3 * (4 - 1.5) / 2
    # = 12.5 + 3 * 2.5 / 2
    # = 12.5 + 7.5 / 2
    # = 12.5 + 3.75
    # = 16.25
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
