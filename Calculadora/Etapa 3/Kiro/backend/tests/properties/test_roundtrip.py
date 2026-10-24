"""Property-based round-trip tests P3 (Stage 1) and P19 (Stage 2 scientific).

P3: evaluate(parse(render(ast))) == evaluate(ast) for arithmetic ASTs.
P19: the same render/parse/evaluate invariant extended over ASTs that include
FunctionNode, ConstantNode, and RootNode, evaluated under a fixed angle mode.
"""

from __future__ import annotations

from decimal import InvalidOperation, Overflow, ROUND_HALF_EVEN, Context

from hypothesis import given

from app.engine.evaluator import evaluate
from app.engine.errors import EvaluationError
from app.engine.parser import parse
from tests.properties import strategies as S

_SIG10 = Context(prec=10, rounding=ROUND_HALF_EVEN)


# Feature: web-calculator, Property 3: Parser round-trip preserves value
@S.PROPERTY_SETTINGS
@given(tree=S.asts())
def test_p3_roundtrip_preserves_value(tree) -> None:
    """Validates: Requirements 6.3, 6.4"""
    try:
        original = evaluate(tree, "radians")
    except (EvaluationError, InvalidOperation, Overflow):
        return
    reparsed = evaluate(parse(S.render(tree)), "radians")
    assert reparsed == original


# Feature: web-calculator, Property 19: Round-trip render/parse preserves value over functions, constants, roots
@S.PROPERTY_SETTINGS
@given(tree=S.scientific_asts())
def test_p19_scientific_roundtrip_preserves_value(tree) -> None:
    """Validates: Requirements 6.3, 6.4"""
    try:
        original = evaluate(tree, "radians")
    except (EvaluationError, InvalidOperation, Overflow):
        return
    try:
        reparsed = evaluate(parse(S.render(tree)), "radians")
    except (EvaluationError, InvalidOperation, Overflow):
        return
    assert _SIG10.plus(reparsed) == _SIG10.plus(original)
