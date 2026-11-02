import pytest
from decimal import Decimal
from src.core.evaluator import evaluate_expression_full
from src.api.v1.errors import CalculatorError

def test_rpn_basic_operations():
    # Test simple addition
    res, stack = evaluate_expression_full("10 20 +", mode="rpn")
    assert res == Decimal("30")
    assert stack == ["30"]

    # Test subtraction, multiplication, division
    res, stack = evaluate_expression_full("12.5 3 *", mode="rpn")
    assert res == Decimal("37.5")
    assert stack == ["37.5"]

    res, stack = evaluate_expression_full("50 10 /", mode="rpn")
    assert res == Decimal("5")
    assert stack == ["5"]

def test_rpn_continuous_stack():
    # Test multiple items pushed to the stack
    res, stack = evaluate_expression_full("10 20 30 40 50", mode="rpn")
    assert res == Decimal("50")
    assert stack == ["10", "20", "30", "40", "50"]

    # Test sequential calculations on accumulated stack items
    res, stack = evaluate_expression_full("10 20 30 40 + * -", mode="rpn")
    # 40 + 30 = 70. 70 * 20 = 1400. 10 - 1400 = -1390.
    assert res == Decimal("-1390")
    assert stack == ["-1390"]

def test_rpn_scientific_functions():
    # Test pi and e in RPN mode
    res, stack = evaluate_expression_full("pi 2 / sin", mode="rpn")
    assert abs(float(res) - 1.0) < 1e-15
    assert len(stack) == 1

    # Test log10, ln, e
    res, stack = evaluate_expression_full("100 log10", mode="rpn")
    assert res == Decimal("2")

    res, stack = evaluate_expression_full("e ln", mode="rpn")
    assert abs(float(res) - 1.0) < 1e-15

    # Test binary root function
    res, stack = evaluate_expression_full("8 3 root", mode="rpn")
    assert res == Decimal("2")

def test_rpn_underflow_errors():
    # Not enough arguments for binary operator
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression_full("5 +", mode="rpn")
    assert exc_info.value.error_code == "STACK_UNDERFLOW"

    # Not enough arguments for scientific function
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression_full("sin", mode="rpn")
    assert exc_info.value.error_code == "STACK_UNDERFLOW"

    # Not enough arguments for binary function
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression_full("8 root", mode="rpn")
    assert exc_info.value.error_code == "STACK_UNDERFLOW"

def test_rpn_division_by_zero():
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression_full("5 0 /", mode="rpn")
    assert exc_info.value.error_code == "DIVISION_BY_ZERO"

def test_rpn_domain_errors():
    with pytest.raises(CalculatorError) as exc_info:
        evaluate_expression_full("-9 sqrt", mode="rpn")
    assert exc_info.value.error_code == "DOMAIN_ERROR"
