"""Property-based tests P4 and P5: division-by-zero and invalid character (task 6.5).
"""

from __future__ import annotations

import pytest
from hypothesis import given

from app.engine import evaluate_expression
from app.engine.errors import DivisionByZeroError, EvaluationError
from tests.properties.strategies import (
    PROPERTY_SETTINGS,
    expressions_with_invalid_character,
    zero_divisor_expressions,
)


# Feature: web-calculator, Property 4: Division by zero always signals an error
@PROPERTY_SETTINGS
@given(expression=zero_divisor_expressions())
def test_p4_division_by_zero_always_errors(expression: str) -> None:
    """Any expression with a zero-valued divisor raises DivisionByZeroError.

    Validates: Requirements 4.1
    """
    with pytest.raises(DivisionByZeroError):
        evaluate_expression(expression)


# Feature: web-calculator, Property 5: Invalid characters always signal an error
@PROPERTY_SETTINGS
@given(expression=expressions_with_invalid_character())
def test_p5_invalid_character_always_errors(expression: str) -> None:
    """Any expression with a disallowed character is rejected, never computed.

    The generator splices a character outside the Stage 1 allowed set into an
    otherwise-valid expression. Depending on the character the Stage 2 engine
    rejects it at a different stage -- a truly disallowed symbol (`&`, `%`)
    is an `InvalidCharacterError` from the tokenizer, an unknown letter run is
    an `InvalidFunctionError`, and a stray valid identifier start (`e`,
    `p`) wedged next to a number is an `InvalidSyntaxError` from the parser.
    In every case the engine raises an `EvaluationError` subclass and returns
    no result, which is the guarantee Requirement 4.4 makes (the input is never
    silently accepted or computed).

    Validates: Requirements 4.4
    """
    with pytest.raises(EvaluationError):
        evaluate_expression(expression)
