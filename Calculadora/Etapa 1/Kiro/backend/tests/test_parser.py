"""Unit tests for the Evaluation_Engine recursive-descent parser (task 2.5).

Covers PEMDAS precedence/associativity structure, unary minus grouping,
parenthesization, and that grammar violations raise the correct error types.

_Requirements: 2.1, 2.2, 2.4, 2.5, 2.6, 4.2, 4.3, 4.5_
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.engine.errors import (
    EmptyExpressionError,
    InvalidSyntaxError,
    UnbalancedParenthesesError,
)
from app.engine.parser import (
    BinaryOpNode,
    NumberNode,
    UnaryOpNode,
    parse,
    render,
)


def N(x: str) -> NumberNode:
    return NumberNode(Decimal(x))


# --------------------------------------------------------------------------- #
# Precedence structure (Requirements 2.1, 2.2)
# --------------------------------------------------------------------------- #
def test_mul_binds_tighter_than_add() -> None:
    # 1 + 2 * 3 -> (1 + (2 * 3))
    tree = parse("1 + 2 * 3")
    assert tree == BinaryOpNode("+", N("1"), BinaryOpNode("*", N("2"), N("3")))


def test_div_binds_tighter_than_sub() -> None:
    tree = parse("8 - 6 / 2")
    assert tree == BinaryOpNode("-", N("8"), BinaryOpNode("/", N("6"), N("2")))


def test_parentheses_override_precedence() -> None:
    # (1 + 2) * 3
    tree = parse("(1 + 2) * 3")
    assert tree == BinaryOpNode("*", BinaryOpNode("+", N("1"), N("2")), N("3"))


def test_nested_parentheses_innermost_first() -> None:
    tree = parse("((1 + 2))")
    assert tree == BinaryOpNode("+", N("1"), N("2"))


# --------------------------------------------------------------------------- #
# Associativity (Requirements 2.4, 2.5)
# --------------------------------------------------------------------------- #
def test_add_sub_left_associative() -> None:
    # 8 - 4 - 2 -> ((8 - 4) - 2)
    tree = parse("8 - 4 - 2")
    assert tree == BinaryOpNode("-", BinaryOpNode("-", N("8"), N("4")), N("2"))


def test_mul_div_left_associative() -> None:
    # 8 / 4 / 2 -> ((8 / 4) / 2)
    tree = parse("8 / 4 / 2")
    assert tree == BinaryOpNode("/", BinaryOpNode("/", N("8"), N("4")), N("2"))


def test_exponent_right_associative() -> None:
    # 2 ^ 2 ^ 3 -> (2 ^ (2 ^ 3))
    tree = parse("2 ^ 2 ^ 3")
    assert tree == BinaryOpNode("^", N("2"), BinaryOpNode("^", N("2"), N("3")))


# --------------------------------------------------------------------------- #
# Unary minus (Requirements 2.6)
# --------------------------------------------------------------------------- #
def test_unary_minus_on_number() -> None:
    assert parse("-5") == UnaryOpNode("-", N("5"))


def test_exponent_binds_tighter_than_unary_minus() -> None:
    # -3 ^ 2 -> -(3 ^ 2)  (so it evaluates to -9)
    tree = parse("-3 ^ 2")
    assert tree == UnaryOpNode("-", BinaryOpNode("^", N("3"), N("2")))


def test_unary_minus_as_exponent_operand() -> None:
    # 2 ^ -3 -> (2 ^ -(3))
    tree = parse("2 ^ -3")
    assert tree == BinaryOpNode("^", N("2"), UnaryOpNode("-", N("3")))


def test_double_unary_minus() -> None:
    assert parse("--5") == UnaryOpNode("-", UnaryOpNode("-", N("5")))


# --------------------------------------------------------------------------- #
# render() round-trip structure (Requirements 2.x, 6.3 support)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "expression",
    ["1 + 2 * 3", "(1 + 2) * 3", "8 - 4 - 2", "2 ^ 2 ^ 3", "-3 ^ 2", "2 ^ -3"],
)
def test_render_reparses_to_equivalent_tree(expression: str) -> None:
    tree = parse(expression)
    assert parse(render(tree)) == tree


# --------------------------------------------------------------------------- #
# Grammar violations (Requirements 4.2, 4.3, 4.5)
# --------------------------------------------------------------------------- #
def test_empty_string_raises_empty_expression() -> None:
    with pytest.raises(EmptyExpressionError):
        parse("")


def test_whitespace_only_raises_empty_expression() -> None:
    with pytest.raises(EmptyExpressionError):
        parse("   ")


@pytest.mark.parametrize("expression", ["3 + * 4", "1 2", "* 5", "4 +"])
def test_invalid_operator_sequence_raises_invalid_syntax(expression: str) -> None:
    with pytest.raises(InvalidSyntaxError):
        parse(expression)


@pytest.mark.parametrize("expression", ["(1 + 2", "((1)", "1 + (2 * 3"])
def test_unclosed_parenthesis_raises_unbalanced(expression: str) -> None:
    with pytest.raises(UnbalancedParenthesesError):
        parse(expression)


def test_unmatched_closing_parenthesis_raises_unbalanced() -> None:
    with pytest.raises(UnbalancedParenthesesError):
        parse("1 + 2)")


def test_invalid_syntax_carries_position() -> None:
    with pytest.raises(InvalidSyntaxError) as exc_info:
        parse("3 + * 4")
    assert exc_info.value.position is not None
    assert exc_info.value.kind == "invalid_syntax"
