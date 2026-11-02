"""Scientific property tests P14, P16, P18 (tasks 27.2, 27.4, 27.6).

Cross-checks the engine's trig/inverse-trig, powers/roots/logs, and constant
substitution against the independent high-precision Decimal oracle in
strategies.py, to at least 10 significant decimal digits, in both angle modes.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, Context

from hypothesis import given
import hypothesis.strategies as st

from app.engine import evaluate_expression
from app.engine.evaluator import evaluate
from app.engine.parser import (
    ConstantNode,
    FunctionNode,
    NumberNode,
    RootNode,
)
from tests.properties import strategies as S

_SIG10 = Context(prec=10, rounding=ROUND_HALF_EVEN)


def _agree_10(a: Decimal, b: Decimal) -> bool:
    return _SIG10.plus(a) == _SIG10.plus(b)


# Feature: web-calculator, Property 14: Trig/inverse-trig match a high-precision reference in both angle modes
@S.PROPERTY_SETTINGS
@given(value=S.trig_operands(), angle_mode=st.sampled_from(["radians", "degrees"]))
def test_p14_sin_cos_match_reference(value: Decimal, angle_mode: str) -> None:
    """Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.6, 24.5"""
    sin_actual = evaluate(FunctionNode("sin", NumberNode(value)), angle_mode)
    cos_actual = evaluate(FunctionNode("cos", NumberNode(value)), angle_mode)
    assert _agree_10(sin_actual, S.reference_sin(value, angle_mode))
    assert _agree_10(cos_actual, S.reference_cos(value, angle_mode))


@S.PROPERTY_SETTINGS
@given(value=S.asin_acos_operands(), angle_mode=st.sampled_from(["radians", "degrees"]))
def test_p14_asin_acos_match_reference(value: Decimal, angle_mode: str) -> None:
    """Validates: Requirements 17.4, 17.6, 24.5 (inverse-trig, principal range)"""
    asin_actual = evaluate(FunctionNode("asin", NumberNode(value)), angle_mode)
    acos_actual = evaluate(FunctionNode("acos", NumberNode(value)), angle_mode)
    assert _agree_10(asin_actual, S.reference_asin(value, angle_mode))
    assert _agree_10(acos_actual, S.reference_acos(value, angle_mode))


@S.PROPERTY_SETTINGS
@given(value=S.atan_operands(), angle_mode=st.sampled_from(["radians", "degrees"]))
def test_p14_atan_matches_reference(value: Decimal, angle_mode: str) -> None:
    """Validates: Requirements 17.4, 17.6, 24.5"""
    actual = evaluate(FunctionNode("atan", NumberNode(value)), angle_mode)
    assert _agree_10(actual, S.reference_atan(value, angle_mode))


# Feature: web-calculator, Property 16: Powers, roots, and logarithms match a Decimal reference
@S.PROPERTY_SETTINGS
@given(value=S.log_operands())
def test_p16_logs_match_reference(value: Decimal) -> None:
    """Validates: Requirements 18.4, 18.5, 18.6, 24.5"""
    ln_actual = evaluate(FunctionNode("ln", NumberNode(value)), "radians")
    log_actual = evaluate(FunctionNode("log10", NumberNode(value)), "radians")
    assert _agree_10(ln_actual, S.reference_ln(value))
    assert _agree_10(log_actual, S.reference_log10(value))


@S.PROPERTY_SETTINGS
@given(value=S.sqrt_operands())
def test_p16_sqrt_matches_reference(value: Decimal) -> None:
    """Validates: Requirements 18.2, 18.6, 24.5"""
    actual = evaluate(FunctionNode("sqrt", NumberNode(value)), "radians")
    assert _agree_10(actual, S.reference_sqrt(value))


@S.PROPERTY_SETTINGS
@given(node=S.root_nodes())
def test_p16_nth_root_matches_reference(node: RootNode) -> None:
    """Validates: Requirements 18.3, 18.6, 24.5"""
    actual = evaluate(node, "radians")
    expected = S.reference_nth_root(node.radicand.value, node.degree.value)
    assert _agree_10(actual, expected)


# Feature: web-calculator, Property 18: Mathematical constants substituted to >=10 significant digits
@S.PROPERTY_SETTINGS
@given(name=st.sampled_from(["pi", "e"]))
def test_p18_constant_substitution(name: str) -> None:
    """Validates: Requirements 19.1, 19.2"""
    actual = evaluate(ConstantNode(name), "radians")
    assert _agree_10(actual, S.reference_constant(name))
