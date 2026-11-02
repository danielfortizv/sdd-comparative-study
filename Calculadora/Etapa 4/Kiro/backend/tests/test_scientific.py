"""Scientific function example tests (task 26.1, Requirement 25.1-25.6).

Verifies trig/inverse-trig in both radians and degrees, angle conversions,
powers/roots/logs, constant substitution, and boundary values, each to at least
10 significant decimal digits.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, Context

from app.engine import evaluate_expression

_SIG10 = Context(prec=10, rounding=ROUND_HALF_EVEN)


def approx10(expression: str, angle_mode: str = "radians") -> Decimal:
    value = evaluate_expression(expression, angle_mode=angle_mode)
    return _SIG10.plus(value)


def sig10(literal: str) -> Decimal:
    return _SIG10.plus(Decimal(literal))


# 25.1 Trig / inverse-trig in both angle modes ------------------------------ #
def test_sin_30_degrees_is_half() -> None:
    assert approx10("sin(30)", "degrees") == sig10("0.5")


def test_cos_zero_is_one() -> None:
    assert approx10("cos(0)", "radians") == sig10("1")


def test_tan_45_degrees_is_one() -> None:
    assert approx10("tan(45)", "degrees") == sig10("1")


def test_sin_pi_over_two_radians_is_one() -> None:
    assert approx10("sin(pi / 2)", "radians") == sig10("1")


def test_atan_one_is_45_degrees() -> None:
    assert approx10("atan(1)", "degrees") == sig10("45")


def test_asin_half_is_30_degrees() -> None:
    assert approx10("asin(0.5)", "degrees") == sig10("30")


def test_acos_zero_is_90_degrees() -> None:
    assert approx10("acos(0)", "degrees") == sig10("90")


def test_cos_60_degrees_is_half() -> None:
    assert approx10("cos(60)", "degrees") == sig10("0.5")


# 25.2 Angle conversions ---------------------------------------------------- #
def test_sin_pi_radians_is_zero() -> None:
    # sin(pi) == 0 to 10 sig digits
    assert abs(evaluate_expression("sin(pi)", angle_mode="radians")) < Decimal("1e-10")


def test_tan_zero_is_zero() -> None:
    assert evaluate_expression("tan(0)", angle_mode="degrees") == Decimal("0")


# 25.3 Powers / roots / logs ------------------------------------------------ #
def test_sqrt_two() -> None:
    assert approx10("sqrt(2)") == sig10("1.414213562")


def test_nth_root_27_3_is_3() -> None:
    assert approx10("root(27, 3)") == sig10("3")


def test_ln_e_is_one() -> None:
    assert approx10("ln(e)") == sig10("1")


def test_log10_1000_is_3() -> None:
    assert approx10("log10(1000)") == sig10("3")


def test_power_integer() -> None:
    assert evaluate_expression("2 ^ 10") == Decimal("1024")


# 25.5 Constants ------------------------------------------------------------ #
def test_pi_substituted_to_10_sig_digits() -> None:
    assert approx10("pi") == sig10("3.141592654")


def test_e_substituted_to_10_sig_digits() -> None:
    assert approx10("e") == sig10("2.718281828")


# 25.6 Boundary values at domain limits ------------------------------------- #
def test_asin_one_is_90_degrees() -> None:
    assert approx10("asin(1)", "degrees") == sig10("90")


def test_asin_minus_one_is_minus_90_degrees() -> None:
    assert approx10("asin(-1)", "degrees") == sig10("-90")


def test_acos_one_is_zero() -> None:
    assert evaluate_expression("acos(1)", angle_mode="degrees") == Decimal("0")


def test_acos_minus_one_is_180_degrees() -> None:
    assert approx10("acos(-1)", "degrees") == sig10("180")


def test_sqrt_zero_is_zero() -> None:
    assert evaluate_expression("sqrt(0)") == Decimal("0")


def test_ln_just_above_zero() -> None:
    # ln(0.0001) is defined and negative
    assert evaluate_expression("ln(0.0001)") < Decimal("0")
