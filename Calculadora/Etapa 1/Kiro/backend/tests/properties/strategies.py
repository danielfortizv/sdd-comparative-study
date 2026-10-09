"""Hypothesis strategies and an independent reference oracle for the engine.

This module is the shared foundation for the backend property-based tests
(design "Testing Strategy" -> "Property-Based Testing"). It provides four
things:

1. A recursive strategy (:func:`asts`) that generates random *valid* arithmetic
   ASTs built from the real engine node types
   (:class:`~app.engine.parser.NumberNode`,
   :class:`~app.engine.parser.UnaryOpNode`,
   :class:`~app.engine.parser.BinaryOpNode`) with bounded depth. Numbers are
   :class:`~decimal.Decimal` values constructed from string literals, and
   division/exponentiation subtrees are constrained so a generated "valid" AST
   actually evaluates (no zero divisors, no pathological exponents). This keeps
   the model-based (P1) and round-trip (P3) properties from being drowned in
   trivially-invalid inputs; division-by-zero is exercised separately by P4.

2. A :func:`render` serializer. It re-exports the engine's own
   :func:`app.engine.parser.render` so the round-trip property (P3) validates
   the production serializer rather than a test-local copy.

3. Invalid-input strategies (:func:`expressions_with_invalid_character`,
   :func:`zero_divisor_expressions`, :func:`over_length_expressions`) used by
   the error properties (P4, P5, P7).

4. An **independent** Decimal reference evaluator (:func:`reference_evaluate`)
   that computes the expected value of an AST under PEMDAS with exact
   ``decimal.Decimal`` arithmetic. It deliberately does **not** import
   :mod:`app.engine.evaluator`, so it is a genuine cross-check for Property 1:
   two independent implementations must agree. It matches the engine's exposed
   rounding contract -- ``ROUND_HALF_EVEN``, at least 10 significant digits for
   a non-terminating result, exact (trailing-zero-stripped) for a terminating
   one, with exponentiation applied before unary minus (which is encoded in the
   AST shape by the parser).

Configuration: :data:`PROPERTY_SETTINGS` is a reusable ``@settings`` profile
with ``max_examples=100`` (design "Configuration": minimum 100 iterations).

_Requirements: 6.1, 6.3, 15.3_
"""

from __future__ import annotations

from decimal import (
    Context,
    Decimal,
    Inexact,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)

from hypothesis import HealthCheck, settings
from hypothesis import strategies as st

# Import the *real* AST node types and the *real* render so generated ASTs and
# their serialization exercise the production engine (Requirement 6.1, 6.3).
# NOTE: we intentionally do NOT import app.engine.evaluator -- the reference
# oracle below must be an independent implementation for Property 1.
from app.engine.parser import BinaryOpNode, NumberNode, UnaryOpNode, render

__all__ = [
    "PROPERTY_SETTINGS",
    "MAX_EXAMPLES",
    "render",
    "asts",
    "numbers",
    "decimal_literals",
    "reference_evaluate",
    "ReferenceError",
    "ReferenceDivisionByZero",
    "expressions_with_invalid_character",
    "zero_divisor_expressions",
    "over_length_expressions",
]


# --------------------------------------------------------------------------- #
# Configuration (design "Configuration": >= 100 iterations)
# --------------------------------------------------------------------------- #
#: Minimum number of examples every property test runs (design mandate).
MAX_EXAMPLES = 100

#: Reusable settings profile for the property tests. ``function_scoped_fixture``
#: is suppressed so tests may combine Hypothesis with pytest fixtures if needed;
#: the recursive AST generation is bounded (see ``asts``) so it stays fast.
PROPERTY_SETTINGS = settings(
    max_examples=MAX_EXAMPLES,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


# --------------------------------------------------------------------------- #
# Reference-evaluator precision model
# --------------------------------------------------------------------------- #
# Mirrors app.engine.evaluator's Decimal Precision Model, but is a fully
# independent implementation (it does not import the evaluator). Property 1
# asserts the two agree, so intentionally reproducing the *contract* (not the
# code) here is what makes the cross-check meaningful.
_WORKING_PRECISION = 50
_MIN_SIGNIFICANT_DIGITS = 10
_REFERENCE_CONTEXT = Context(prec=_WORKING_PRECISION, rounding=ROUND_HALF_EVEN)

#: Number-generation bounds. Kept modest so power operations stay well-defined
#: and (where possible) terminating, and so chained expressions do not overflow
#: the working precision before the >=10 significant-digit contract is applied.
_MAX_INT_DIGITS = 4
_MAX_FRAC_DIGITS = 3

#: Exponents are restricted to small *positive* integers so ``^`` is always
#: well-defined and terminating (design task note: "keep exponents small
#: integers so power operations are well-defined and terminating where
#: possible"). A negative base with a fractional exponent has no real value,
#: ``0 ^ 0`` is undefined for the engine's Decimal power, and large exponents
#: blow past the working precision; a small positive integer exponent avoids all
#: three (any base, including zero, raised to a positive integer is defined and
#: terminating).
_MIN_EXPONENT = 1
_MAX_EXPONENT = 4

#: Recursion bounds for the AST generator.
_MAX_DEPTH = 4


# --------------------------------------------------------------------------- #
# Reference oracle errors (independent of app.engine.errors)
# --------------------------------------------------------------------------- #
class ReferenceError(Exception):
    """Base error for the independent reference evaluator."""


class ReferenceDivisionByZero(ReferenceError):
    """Raised by the reference evaluator when a divisor evaluates to zero.

    Generated *valid* ASTs never trigger this (division subtrees are guarded),
    but the reference evaluator still detects it so it can be reused by the
    division-by-zero property (P4) and to guard exponentiation edge cases.
    """


# --------------------------------------------------------------------------- #
# Leaf strategies: Decimal number literals
# --------------------------------------------------------------------------- #
def decimal_literals(
    *,
    allow_zero: bool = True,
    max_int_digits: int = _MAX_INT_DIGITS,
    max_frac_digits: int = _MAX_FRAC_DIGITS,
) -> st.SearchStrategy[Decimal]:
    """A strategy of non-negative :class:`Decimal` values built from string.

    Values are assembled from digit strings and turned into ``Decimal`` via
    ``Decimal(str)`` -- never via ``float`` -- so operands are exact
    (Requirement 3.3). The sign is *not* modelled here: unary minus is its own
    AST node (:class:`UnaryOpNode`), matching how the parser represents negative
    numbers.

    Args:
        allow_zero: When ``False``, the generated value is guaranteed non-zero.
            Used to build safe divisors so generated valid ASTs evaluate
            without dividing by zero.
        max_int_digits: Maximum number of integer-part digits.
        max_frac_digits: Maximum number of fractional-part digits.
    """
    int_part = st.text(alphabet="0123456789", min_size=1, max_size=max_int_digits)
    frac_part = st.text(alphabet="0123456789", min_size=1, max_size=max_frac_digits)

    def _build(integer: str, fraction: str | None) -> Decimal:
        literal = integer if fraction is None else f"{integer}.{fraction}"
        return Decimal(literal)

    strategy = st.builds(_build, int_part, st.none() | frac_part)
    if not allow_zero:
        strategy = strategy.filter(lambda d: d != 0)
    return strategy


def numbers(**kwargs) -> st.SearchStrategy[NumberNode]:
    """A strategy of :class:`NumberNode` leaves wrapping exact Decimals."""
    return decimal_literals(**kwargs).map(NumberNode)


def _exponents() -> st.SearchStrategy[NumberNode]:
    """Small positive integer exponents as :class:`NumberNode` leaves.

    Restricting the exponent keeps ``^`` well-defined and terminating for any
    generated base (including zero), so power subtrees never produce a
    NaN/overflow (or the undefined ``0 ^ 0``) that the engine would reject as
    invalid syntax.
    """
    return st.integers(min_value=_MIN_EXPONENT, max_value=_MAX_EXPONENT).map(
        lambda n: NumberNode(Decimal(n))
    )


# --------------------------------------------------------------------------- #
# Recursive AST strategy (design "Generators")
# --------------------------------------------------------------------------- #
def asts(max_depth: int = _MAX_DEPTH) -> st.SearchStrategy:
    """A recursive strategy generating valid arithmetic ASTs.

    The tree is built from the real engine node types and is bounded by
    ``max_depth``. Constraints keep every generated tree *evaluable* so it is a
    useful input for the model-based (P1) and round-trip (P3) properties:

    * ``/`` right operands are drawn from a non-zero divisor sub-strategy, so a
      generated valid AST never divides by zero (P4 covers that case with its
      own generator).
    * ``^`` right operands are small positive integers, so exponentiation is
      always well-defined and terminating for any base.
    * ``+ - *`` combine arbitrary sub-ASTs.
    * Unary minus wraps any sub-AST.

    A "parenthesized expression" is represented implicitly: nesting a
    :class:`BinaryOpNode` inside another produces the same tree the parser
    builds for a parenthesized subexpression, and :func:`render` re-inserts the
    parentheses needed to preserve that structure.

    Args:
        max_depth: Maximum recursion depth. ``0`` yields only number leaves.

    Returns:
        A Hypothesis strategy producing ``Node`` values.
    """
    leaves = numbers()

    def _extend(children: st.SearchStrategy) -> st.SearchStrategy:
        # Additive/multiplicative binary ops over two arbitrary children.
        additive_multiplicative = st.builds(
            BinaryOpNode,
            st.sampled_from(["+", "-", "*"]),
            children,
            children,
        )
        # Division: guard the divisor so the tree stays evaluable. The divisor
        # is a *non-zero* leaf (or a small safe subtree) rather than an
        # arbitrary child, since an arbitrary child could evaluate to zero.
        division = st.builds(
            lambda left, right: BinaryOpNode("/", left, right),
            children,
            numbers(allow_zero=False),
        )
        # Exponentiation: arbitrary base, small positive integer exponent.
        power = st.builds(
            lambda base, exp: BinaryOpNode("^", base, exp),
            children,
            _exponents(),
        )
        # Unary minus over any child.
        unary = st.builds(lambda operand: UnaryOpNode("-", operand), children)
        return st.one_of(additive_multiplicative, division, power, unary)

    # ``max_leaves`` bounds the tree size (roughly the number of number leaves).
    # Kept modest so nested power/`*` stacks do not overflow the working
    # precision and Hypothesis does not build unwieldy reprs.
    return st.recursive(leaves, _extend, max_leaves=max_depth * 2)


# --------------------------------------------------------------------------- #
# Independent Decimal reference evaluator (Property 1 oracle)
# --------------------------------------------------------------------------- #
def reference_evaluate(node) -> Decimal:
    """Evaluate an AST with exact Decimal arithmetic, independently of the engine.

    This is the reference oracle for Property 1. It walks the same AST the
    engine walks but with its own recursion and its own precision handling, so
    agreement between this function and ``app.engine.evaluator.evaluate`` is a
    real cross-check rather than a tautology.

    Semantics (matching the engine's exposed contract, design "Decimal
    Precision Model"):

    * ``+ - * /`` and ``^`` computed under a ``prec=50`` ``ROUND_HALF_EVEN``
      context.
    * Exponentiation is applied before unary minus. This ordering lives in the
      AST shape produced by the parser (``-3^2`` -> ``-(3^2)``), so simply
      walking the tree honors it.
    * A terminating result is returned with trailing fractional zeros stripped.
    * A non-terminating result is rounded to at least 10 significant digits with
      ``ROUND_HALF_EVEN``.

    Args:
        node: The AST root (a ``NumberNode``/``UnaryOpNode``/``BinaryOpNode``).

    Returns:
        The expected :class:`Decimal` result.

    Raises:
        ReferenceDivisionByZero: If a divisor subexpression evaluates to zero.
        ReferenceError: On an unrecognized node or undefined exponentiation.
    """
    with localcontext(_REFERENCE_CONTEXT) as ctx:
        ctx.clear_flags()
        raw = _reference_eval(node, ctx)
        was_inexact = bool(ctx.flags[Inexact])
        return _reference_finalize(raw, was_inexact)


def _reference_eval(node, ctx: Context) -> Decimal:
    """Recursive core of :func:`reference_evaluate`."""
    if isinstance(node, NumberNode):
        return +node.value

    if isinstance(node, UnaryOpNode):
        operand = _reference_eval(node.operand, ctx)
        if node.op == "-":
            return ctx.minus(operand)
        raise ReferenceError(f"Unsupported unary operator {node.op!r}.")

    if isinstance(node, BinaryOpNode):
        left = _reference_eval(node.left, ctx)
        right = _reference_eval(node.right, ctx)
        op = node.op
        if op == "+":
            return ctx.add(left, right)
        if op == "-":
            return ctx.subtract(left, right)
        if op == "*":
            return ctx.multiply(left, right)
        if op == "/":
            if right == 0:
                raise ReferenceDivisionByZero("Division by zero is not allowed.")
            return ctx.divide(left, right)
        if op == "^":
            return _reference_power(left, right, ctx)
        raise ReferenceError(f"Unsupported binary operator {op!r}.")

    raise ReferenceError(f"Cannot evaluate unknown AST node: {node!r}.")


def _reference_power(base: Decimal, exponent: Decimal, ctx: Context) -> Decimal:
    """Raise ``base`` to ``exponent`` for the reference evaluator."""
    if base == 0 and exponent < 0:
        raise ReferenceDivisionByZero("Division by zero is not allowed.")
    try:
        result = ctx.power(base, exponent)
    except (InvalidOperation, Overflow) as exc:
        raise ReferenceError("Undefined exponentiation.") from exc
    if result.is_nan() or result.is_infinite():
        raise ReferenceError("Undefined exponentiation.")
    return result


def _reference_finalize(value: Decimal, was_inexact: bool) -> Decimal:
    """Normalize/round a raw reference value to match the engine's contract."""
    if not value.is_finite():  # pragma: no cover - guarded upstream
        return value
    if value == 0:
        return Decimal(0)
    if was_inexact:
        rounding_ctx = Context(
            prec=_MIN_SIGNIFICANT_DIGITS, rounding=ROUND_HALF_EVEN
        )
        value = rounding_ctx.plus(value)
    return _strip_trailing_zeros(value)


def _strip_trailing_zeros(value: Decimal) -> Decimal:
    """Collapse trailing fractional zeros without exponent-formatting integers."""
    if value == 0:
        return Decimal(0)
    normalized = value.normalize(_REFERENCE_CONTEXT)
    exponent = normalized.as_tuple().exponent
    if isinstance(exponent, int) and exponent > 0:
        return normalized.quantize(Decimal(1), context=_REFERENCE_CONTEXT)
    return normalized


# --------------------------------------------------------------------------- #
# Invalid-input strategies (P4, P5, P7)
# --------------------------------------------------------------------------- #
#: Characters the tokenizer accepts (digits, decimal point, operators, parens,
#: and whitespace). Anything else is an InvalidCharacterError (Requirement 4.4).
_ALLOWED_CHARS = set("0123456789.+-*/^() \t\n\r")


def expressions_with_invalid_character() -> st.SearchStrategy[str]:
    """Otherwise-plausible expressions with a single disallowed character.

    Used by Property 5. A disallowed character (e.g. a letter, ``&``, ``%``) is
    spliced into an otherwise-simple expression at a random position; the
    tokenizer must reject the resulting string.
    """
    disallowed = st.characters(
        min_codepoint=33,
        max_codepoint=126,
    ).filter(lambda c: c not in _ALLOWED_CHARS)

    base = st.sampled_from(
        [
            "1+2",
            "3*4",
            "10/2",
            "2^3",
            "(1+2)*3",
            "5-3+1",
            "12.5+3",
        ]
    )

    def _splice(expr: str, bad: str, index: int) -> str:
        i = index % (len(expr) + 1)
        return expr[:i] + bad + expr[i:]

    return st.builds(_splice, base, disallowed, st.integers(min_value=0, max_value=32))


def zero_divisor_expressions() -> st.SearchStrategy[str]:
    """Expressions whose divisor subexpression evaluates to zero (Property 4).

    Produces strings of the form ``<numerator> / <zero-expr>`` where the
    divisor is a subexpression that evaluates to zero (a literal ``0``, a
    difference of equal values, or a product with a zero factor). Rendered with
    the engine's :func:`render` so they are guaranteed parseable.
    """
    numerator = numbers()

    def _zero_forms() -> st.SearchStrategy:
        literal_zero = st.just(NumberNode(Decimal(0)))
        # n - n == 0
        self_diff = decimal_literals().map(
            lambda d: BinaryOpNode("-", NumberNode(d), NumberNode(d))
        )
        # 0 * n == 0
        zero_product = numbers().map(
            lambda n: BinaryOpNode("*", NumberNode(Decimal(0)), n)
        )
        return st.one_of(literal_zero, self_diff, zero_product)

    return st.builds(
        lambda num, zero: render(BinaryOpNode("/", num, zero)),
        numerator,
        _zero_forms(),
    )


def over_length_expressions(max_length: int = 256) -> st.SearchStrategy[str]:
    """Valid-looking expression strings longer than ``max_length`` (Property 7).

    The string is a chain of ``1+1+1+...`` padded to exceed the limit, so it is
    rejected purely for length rather than for a grammar or character error.
    """
    min_len = max_length + 1

    def _build(extra: int) -> str:
        target = min_len + extra
        # "1" then repeated "+1"; length = 1 + 2*k. Grow k until we pass target.
        k = (target - 1 + 1) // 2 + 1
        expr = "1" + "+1" * k
        return expr

    return st.integers(min_value=0, max_value=256).map(_build).filter(
        lambda s: len(s) > max_length
    )
