"""Decimal evaluator for the Evaluation_Engine.

Walks the AST produced by :mod:`app.engine.parser` and computes an exact
:class:`~decimal.Decimal` result. It is the third and final stage of the pure
computation core (tokenizer -> parser -> evaluator) and is HTTP-agnostic.

Design highlights ("Decimal Precision Model"):

* All arithmetic runs under a module-level :class:`decimal.Context` with a
  generous working precision (``prec = 50``) so intermediate operations do not
  lose significance (Requirements 1.2, 1.3, 3.3).
* Operands are the exact :class:`~decimal.Decimal` values carried by
  :class:`~app.engine.parser.NumberNode`, which the parser built via
  ``Decimal(lexeme)`` directly from the source text -- never via ``float`` --
  so ``0.1 + 0.2`` is computed from the exact operands ``0.1`` and ``0.2``
  (Requirement 3.3).
* A divisor subexpression that evaluates to zero raises
  :class:`~app.engine.errors.DivisionByZeroError` (Requirement 4.1).
* A terminating result is normalized so trailing zeros collapse and
  ``0.1 + 0.2`` yields exactly ``0.3`` (Requirements 3.1, 3.2).
* A non-terminating result (e.g. ``1 / 3``) is rounded to at least 10
  significant decimal digits using ``ROUND_HALF_EVEN`` (Requirement 3.4).
* Exponentiation binds tighter than unary minus. This is encoded in the AST
  shape by the parser (``-3^2`` parses as ``-(3^2)``); the evaluator simply
  walks that structure and therefore applies the exponent before the unary
  minus (Requirements 2.3, 2.6).
"""

from __future__ import annotations

from decimal import (
    Context,
    Decimal,
    DivisionByZero as _DecimalDivisionByZero,
    Inexact,
    InvalidOperation,
    Overflow,
    ROUND_HALF_EVEN,
    localcontext,
)

from . import scientific  # noqa: F401 - imported as module for dispatch
from .constants import constant_value
from .errors import DivisionByZeroError, DomainError, InvalidSyntaxError
from .parser import (
    BinaryOpNode,
    ConstantNode,
    FunctionNode,
    Node,
    NumberNode,
    RootNode,
    UnaryOpNode,
)

#: Default angle mode. Trig / inverse-trig nodes interpret/produce angles in
#: radians unless the caller threads ``"degrees"`` through (Requirements 17.9,
#: 24.3). Every other node ignores the mode entirely.
_DEFAULT_ANGLE_MODE = "radians"

# --------------------------------------------------------------------------- #
# Precision configuration
# --------------------------------------------------------------------------- #
#: Working precision for all intermediate arithmetic. Chosen generously (well
#: above the >=10 significant digits the contract exposes) so that intermediate
#: operations in a chained expression do not accumulate rounding error before
#: the final result is normalized/rounded (Requirements 1.2, 1.3, 3.3).
_WORKING_PRECISION = 50

#: Minimum number of significant decimal digits retained for a non-terminating
#: result (Requirement 3.4).
_MIN_SIGNIFICANT_DIGITS = 10

#: The module-level context every evaluation runs under. Rounding is
#: round-half-to-even (banker's rounding) per Requirement 3.4.
_CONTEXT = Context(prec=_WORKING_PRECISION, rounding=ROUND_HALF_EVEN)


def evaluate(node: Node, angle_mode: str = _DEFAULT_ANGLE_MODE) -> Decimal:
    """Evaluate an AST ``node`` to an exact, normalized :class:`Decimal`.

    The whole walk runs inside a copy of the module-level decimal context so the
    caller's ambient context is never mutated. The raw computed value is then
    normalized/rounded for presentation (see :func:`_finalize`).

    Args:
        node: The root AST node returned by :func:`app.engine.parser.parse`.
        angle_mode: ``"radians"`` (default) or ``"degrees"``. Threaded through
            the walk and consulted only by trig / inverse-trig
            :class:`~app.engine.parser.FunctionNode` evaluation; every other node
            (and all Stage 1 arithmetic) ignores it, so non-trig behavior is
            identical regardless of mode (Requirements 17.9, 19.1, 19.2, 24.3).

    Returns:
        The result as a :class:`~decimal.Decimal`. Terminating results are
        normalized (no misleading trailing zeros); non-terminating results --
        including irrational scientific results such as ``sqrt(2)`` or ``ln(2)``
        -- are rounded to at least 10 significant digits with ``ROUND_HALF_EVEN``
        (Requirements 3.4, 17.6, 18.6).

    Raises:
        DivisionByZeroError: If any divisor subexpression evaluates to zero
            (Requirement 4.1).
        DomainError: If a scientific node violates its mathematical domain
            (e.g. ``sqrt(-1)``, ``asin(2)``, ``tan(90 deg)``, a negative base to
            a non-integer exponent) (Requirements 17.7, 17.8, 18.7-18.11).
        InvalidSyntaxError: If an operator or node shape is not recognized
            (defensive; a well-formed AST never triggers this).
    """
    with localcontext(_CONTEXT) as ctx:
        # Clear the inexact flag so that, after the walk, it tells us whether any
        # operation lost significance (i.e. produced a non-terminating expansion
        # that had to be rounded to the working precision). An exact result keeps
        # the flag clear no matter how many significant digits it carries.
        ctx.clear_flags()
        raw = _eval(node, ctx, angle_mode)
        was_inexact = bool(ctx.flags[Inexact])
        return _finalize(raw, was_inexact, ctx)


def _eval(node: Node, ctx: Context, angle_mode: str) -> Decimal:
    """Recursively evaluate ``node`` under the active context ``ctx``.

    ``angle_mode`` is threaded through every recursive call so a nested trig
    function anywhere in the tree sees the caller's mode; only
    :class:`~app.engine.parser.FunctionNode` trig evaluation actually consults
    it (Requirements 17.1-17.4).
    """
    if isinstance(node, NumberNode):
        # The operand is already an exact Decimal built from its lexeme by the
        # parser; re-apply the context so it participates at working precision.
        return +node.value

    if isinstance(node, ConstantNode):
        # A named constant (pi / e) resolves to its exact >=50-digit Decimal;
        # re-apply the context so it participates at the working precision, just
        # like a NumberNode operand (Requirements 19.1, 19.2).
        return +constant_value(node.name)

    if isinstance(node, UnaryOpNode):
        operand = _eval(node.operand, ctx, angle_mode)
        if node.op == "-":
            return ctx.minus(operand)
        raise InvalidSyntaxError(  # pragma: no cover - defensive
            message=f"Unsupported unary operator '{node.op}'."
        )

    if isinstance(node, BinaryOpNode):
        left = _eval(node.left, ctx, angle_mode)
        right = _eval(node.right, ctx, angle_mode)
        return _apply_binary(node.op, left, right, ctx)

    if isinstance(node, FunctionNode):
        # Evaluate the argument first (threading angle_mode so nested trig sees
        # the caller's mode), then dispatch to the Decimal-native kernel. The
        # scientific helper runs in its own guard-digit localcontext and returns
        # a full-precision Decimal; re-apply our context via unary plus so the
        # value participates at the evaluator's working precision and sets the
        # Inexact flag when it is non-terminating (Requirements 17.1-17.4, 18.5).
        operand_value = _eval(node.operand, ctx, angle_mode)
        result = scientific.apply_function(node.name, operand_value, angle_mode)
        return +result

    if isinstance(node, RootNode):
        # Evaluate both arguments, then dispatch to the n-th root kernel. As with
        # FunctionNode, the helper runs in its own context and returns a
        # full-precision Decimal re-applied here (Requirement 18.3).
        radicand_value = _eval(node.radicand, ctx, angle_mode)
        degree_value = _eval(node.degree, ctx, angle_mode)
        result = scientific.nth_root(radicand_value, degree_value)
        return +result

    raise InvalidSyntaxError(  # pragma: no cover - defensive
        message=f"Cannot evaluate unknown AST node: {node!r}."
    )


def _apply_binary(op: str, left: Decimal, right: Decimal, ctx: Context) -> Decimal:
    """Apply a binary operator to two already-evaluated operands."""
    if op == "+":
        return ctx.add(left, right)
    if op == "-":
        return ctx.subtract(left, right)
    if op == "*":
        return ctx.multiply(left, right)
    if op == "/":
        if right == 0:
            raise DivisionByZeroError()
        return ctx.divide(left, right)
    if op == "^":
        return _power(left, right, ctx)
    raise InvalidSyntaxError(  # pragma: no cover - defensive
        message=f"Unsupported binary operator '{op}'."
    )


def _power(base: Decimal, exponent: Decimal, ctx: Context) -> Decimal:
    """Raise ``base`` to ``exponent`` under the working context.

    ``decimal.Context.power`` handles integer, negative, and fractional
    exponents. Two edge cases are translated into the engine's error taxonomy:

    * ``0 ** negative`` is a division by zero (``1 / 0**n``) and surfaces as
      :class:`DivisionByZeroError` (Requirement 4.1).
    * A negative base raised to a non-integer exponent has no real value and
      surfaces as :class:`DomainError` (Requirement 18.9), e.g. ``(-8)^0.5``.
      Integer-ness is decided in Decimal via
      ``exponent == exponent.to_integral_value()`` so ``(-8)^2`` and ``(-8)^-1``
      remain valid.
    * Any other base/exponent combination with no real value, or a result that
      overflows / comes back as ``NaN``/``Infinity``, surfaces as
      :class:`InvalidSyntaxError` rather than leaking a decimal ``NaN`` (Stage 1
      behavior, left intact to avoid regressing Stage 1 tests).

    A non-representable-but-valid power (irrational result) is left to
    :func:`_finalize`, which rounds it to >=10 significant digits.
    """
    if base == 0 and exponent < 0:
        raise DivisionByZeroError()
    if base < 0 and exponent != exponent.to_integral_value():
        raise DomainError(
            message="A negative base cannot be raised to a non-integer power."
        )
    try:
        result = ctx.power(base, exponent)
    except _DecimalDivisionByZero as exc:  # pragma: no cover - guarded above
        raise DivisionByZeroError() from exc
    except (InvalidOperation, Overflow) as exc:
        raise InvalidSyntaxError(
            message="The expression contains an undefined exponentiation."
        ) from exc
    if result.is_nan() or result.is_infinite():
        raise InvalidSyntaxError(
            message="The expression contains an undefined exponentiation."
        )
    return result


def _finalize(value: Decimal, was_inexact: bool, ctx: Context) -> Decimal:
    """Normalize/round the raw computed ``value`` for presentation.

    Two outcomes, per the Decimal Precision Model, discriminated by whether the
    computation was *exact*:

    * **Terminating** value (``was_inexact`` is ``False``): every operation was
      exact, so the value is the true mathematical result. Strip trailing
      fractional zeros so it reads cleanly (``0.1 + 0.2`` -> ``0.3`` rather than
      ``0.3000...``) while keeping integers as plain integers (``4`` rather than
      ``4E+0``). No rounding occurs, and an exact value keeps all of its
      significant digits regardless of how many there are (Requirements 3.1, 3.2).
    * **Non-terminating** value (``was_inexact`` is ``True``): some operation
      (e.g. ``1 / 3``) lost significance and was rounded to the working
      precision under ``ROUND_HALF_EVEN``. Re-round it to at least
      ``_MIN_SIGNIFICANT_DIGITS`` significant digits so the exposed result has
      the mandated minimum precision without carrying the full 50-digit tail
      (Requirement 3.4).

    Using the inexact flag rather than a digit-count heuristic ensures an exact
    result with many significant digits (e.g. ``123456.78912``) is returned
    verbatim instead of being wrongly truncated.
    """
    if not value.is_finite():  # pragma: no cover - guarded upstream
        return value

    if was_inexact:
        rounded = _round_to_significant_digits(
            value, _MIN_SIGNIFICANT_DIGITS, ctx
        )
        return _strip_trailing_zeros(rounded, ctx)

    return _strip_trailing_zeros(value, ctx)


def _round_to_significant_digits(value: Decimal, sig_digits: int, ctx: Context) -> Decimal:
    """Round ``value`` to ``sig_digits`` significant digits, round-half-even."""
    if value == 0:
        return Decimal(0)
    rounding_ctx = Context(prec=sig_digits, rounding=ROUND_HALF_EVEN)
    return rounding_ctx.plus(value)


def _strip_trailing_zeros(value: Decimal, ctx: Context) -> Decimal:
    """Remove trailing fractional zeros without turning integers into exponents.

    ``Decimal.normalize`` collapses e.g. ``Decimal("10")`` to ``Decimal("1E+1")``.
    That is mathematically equal but reads poorly, so integral values are
    quantized back to a zero-exponent form.
    """
    if value == 0:
        return Decimal(0)
    normalized = value.normalize(ctx)
    exponent = normalized.as_tuple().exponent
    if isinstance(exponent, int) and exponent > 0:
        # Integral magnitude expressed with a positive exponent (e.g. 1E+1):
        # re-expand to a plain integer form (10) via quantize to 1.
        return normalized.quantize(Decimal(1), context=ctx)
    return normalized


def evaluate_ast(node: Node, angle_mode: str = _DEFAULT_ANGLE_MODE) -> Decimal:
    """Alias for :func:`evaluate`.

    Provided for callers/tests that prefer an explicit ``evaluate_ast`` name to
    distinguish AST evaluation from the higher-level ``evaluate_expression``
    entry point (see :mod:`app.engine`). ``angle_mode`` is threaded through
    unchanged (default radians).
    """
    return evaluate(node, angle_mode)


__all__ = ["evaluate", "evaluate_ast"]
