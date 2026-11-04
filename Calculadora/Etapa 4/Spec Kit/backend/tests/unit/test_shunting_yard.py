import pytest
from src.core.evaluator import tokenize, process_unary_operators, infix_to_postfix
from src.api.v1.errors import CalculatorError

def test_infix_to_postfix_basic():
    # Simple addition
    toks = process_unary_operators(tokenize("10 + 20"))
    postfix = infix_to_postfix(toks)
    assert postfix == ["10", "20", "+"]

    # PEMDAS Precedence checks
    toks = process_unary_operators(tokenize("12.5 + 3 * (4 - 1.5) / 2"))
    postfix = infix_to_postfix(toks)
    assert postfix == ["12.5", "3", "4", "1.5", "-", "*", "2", "/", "+"]

def test_shunting_yard_unary():
    # Leading unary minus
    toks = process_unary_operators(tokenize("-5 + 3"))
    postfix = infix_to_postfix(toks)
    assert postfix == ["5", "u-", "3", "+"]

    # Unary plus
    toks = process_unary_operators(tokenize("+5 * +3"))
    postfix = infix_to_postfix(toks)
    assert postfix == ["5", "u+", "3", "u+", "*"]

def test_shunting_yard_functions():
    # Single argument scientific function
    toks = process_unary_operators(tokenize("sin(pi / 2)"))
    postfix = infix_to_postfix(toks)
    assert postfix == ["pi", "2", "/", "sin"]

    # Two argument root function
    toks = process_unary_operators(tokenize("root(8, 3)"))
    postfix = infix_to_postfix(toks)
    assert postfix == ["8", "3", "root"]

def test_shunting_yard_mismatched_parentheses():
    # Unclosed open parenthesis
    toks = process_unary_operators(tokenize("(1 + 2"))
    with pytest.raises(CalculatorError) as exc_info:
        infix_to_postfix(toks)
    assert "Mismatched parentheses" in exc_info.value.details

    # Mismatched closing parenthesis
    toks = process_unary_operators(tokenize("1 + 2)"))
    with pytest.raises(CalculatorError) as exc_info:
        infix_to_postfix(toks)
    assert "Mismatched parentheses" in exc_info.value.details
