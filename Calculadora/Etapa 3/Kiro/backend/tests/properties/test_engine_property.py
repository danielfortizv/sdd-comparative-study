"""Property-based tests P1 and P2 for the Evaluation_Engine (tasks 6.2, 6.3).

P1 cross-checks the engine against an independent Decimal reference evaluation
of the same parsed AST; P2 checks that a non-terminating division is rounded to
at least 10 significant digits with round-half-even.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, localcontext, Context

from hypothesis import given

from app.engine import evaluate_expression
from app.engine.evaluator import evaluate
from tests.properties.strategies import (
    PROPERTY_SETTINGS,
    asts,
    reference_evaluate,
    render,
)


# Feature: web-calculator, Property 1: Engine matches PEMDAS/Decimal reference evaluation
@PROPERTY_SETTINGS
@given(tree=asts())
def test_p1_engine_matches_reference(tree) -> None:
    """The engine result equals an independent Decimal reference of the AST.

    Validates: Requirements 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6,
    3.2, 3.3, 6.1
    """
    expected = reference_evaluate(tree)
    actual = evaluate(tree, "radians")
    assert actual == expected


# Feature: web-calculator, Property 2: Non-terminating division rounded to >=10 sig digits (round-half-even)
@PROPERTY_SETTINGS
@given(
    numerator=__import__("hypothesis").strategies.integers(min_value=1, max_value=9999),
    denominator=__import__("hypothesis").strategies.integers(min_value=1, max_value=9999),
)
def test_p2_non_terminating_division_rounding(numerator: int, denominator: int) -> None:
    """A division result matches a >=10-sig-digit round-half-even reference.

    Validates: Requirements 3.4
    """
    expression = f"{numerator} / {denominator}"
    actual = evaluate_expression(expression)

    # Independent reference: divide under a 10-significant-digit half-even
    # context, then strip trailing zeros (matching the engine's finalize).
    with localcontext(Context(prec=50, rounding=ROUND_HALF_EVEN)) as ctx:
        ctx.clear_flags()
        raw = Decimal(numerator) / Decimal(denominator)
        inexact = bool(ctx.flags[__import__("decimal").Inexact])
    if inexact:
        ref_ctx = Context(prec=10, rounding=ROUND_HALF_EVEN)
        expected = ref_ctx.plus(raw)
    else:
        expected = raw
    # Compare numeric value to >=10 significant digits.
    assert actual == +Context(prec=10, rounding=ROUND_HALF_EVEN).plus(expected)
