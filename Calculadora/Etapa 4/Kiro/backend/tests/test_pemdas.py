"""PEMDAS, associativity, and decimal-exactness unit tests (task 5.1).

Verifies conventional order-of-operations results across multiple precedence
levels, operator associativity, unary-minus/exponent interaction, and exact
decimal arithmetic, each asserting the exact expected :class:~decimal.Decimal.

_Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 15.1_
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.engine import evaluate_expression


def E(expression: str) -> Decimal:
    return evaluate_expression(expression)


# --------------------------------------------------------------------------- #
# PEMDAS across >=3 precedence levels (Requirements 1.1, 1.2, 1.4, 2.1-2.3)
# --------------------------------------------------------------------------- #
def test_pemdas_add_mul_exponent() -> None:
    # 2 + 3 * 4 ^ 2 = 2 + 3 * 16 = 2 + 48 = 50
    assert E("2 + 3 * 4 ^ 2") == Decimal("50")


def test_pemdas_with_parentheses_and_decimals() -> None:
    # 12.5 + 3 * (4 - 1.5) / 2 = 12.5 + 3 * 2.5 / 2 = 12.5 + 3.75 = 16.25
    assert E("12.5 + 3 * (4 - 1.5) / 2") == Decimal("16.25")


def test_parentheses_override_default_precedence() -> None:
    assert E("(2 + 3) * 4") == Decimal("20")
    assert E("2 + 3 * 4") == Decimal("14")


def test_nested_parentheses_innermost_first() -> None:
    # ((1 + 2) * (3 + 4)) = 3 * 7 = 21
    assert E("((1 + 2) * (3 + 4))") == Decimal("21")


# --------------------------------------------------------------------------- #
# Associativity (Requirements 2.4, 2.5)
# --------------------------------------------------------------------------- #
def test_exponent_right_associative() -> None:
    # 2 ^ 2 ^ 3 = 2 ^ (2 ^ 3) = 2 ^ 8 = 256
    assert E("2 ^ 2 ^ 3") == Decimal("256")


def test_division_left_associative() -> None:
    # 8 / 4 / 2 = (8 / 4) / 2 = 1
    assert E("8 / 4 / 2") == Decimal("1")


def test_subtraction_left_associative() -> None:
    # 8 - 4 - 2 = (8 - 4) - 2 = 2
    assert E("8 - 4 - 2") == Decimal("2")


# --------------------------------------------------------------------------- #
# Unary minus vs exponent (Requirement 2.6)
# --------------------------------------------------------------------------- #
def test_unary_minus_looser_than_exponent() -> None:
    # -3 ^ 2 = -(3 ^ 2) = -9
    assert E("-3 ^ 2") == Decimal("-9")


def test_unary_minus_on_parenthesized_base() -> None:
    # (-3) ^ 2 = 9
    assert E("(-3) ^ 2") == Decimal("9")


# --------------------------------------------------------------------------- #
# Exact decimal arithmetic (Requirements 3.1, 3.2)
# --------------------------------------------------------------------------- #
def test_point_one_plus_point_two_is_exactly_point_three() -> None:
    assert E("0.1 + 0.2") == Decimal("0.3")


def test_terminating_decimal_result_is_exact() -> None:
    # 1.1 * 1.1 = 1.21 exactly (no binary float error)
    assert E("1.1 * 1.1") == Decimal("1.21")


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1 + 1", "2"),
        ("10 / 4", "2.5"),
        ("0.1 + 0.2 + 0.3", "0.6"),
        ("100 - 0.01", "99.99"),
    ],
)
def test_assorted_exact_values(expression: str, expected: str) -> None:
    assert E(expression) == Decimal(expected)
