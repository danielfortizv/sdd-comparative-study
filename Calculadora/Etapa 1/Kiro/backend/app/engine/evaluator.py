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

from .errors import DivisionByZeroError, InvalidSyntaxError
from .parser import BinaryOpNode, Node, NumberNode, UnaryOpNode

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


def evaluate(node: Node) -> Decimal:
    """Evaluate an AST ``node`` to an exact, normalized :class:`Decimal`.

    The whole walk runs inside a copy of the module-level decimal context so the
    caller's ambient context is never mutated. The raw computed value is then
    normalized/rounded for presentation (see :func:`_finalize`).

    Args:
        node: The root AST node returned by :func:`app.engine.parser.parse`.

    Returns:
        The result as a :class:`~decimal.Decimal`. Terminating results are
        normalized (no misleading trailing zeros); non-terminating results are
        rounded to at least 10 significant digits with ``ROUND_HALF_EVEN``.

    Raises:
        DivisionByZeroError: If any divisor subexpression evaluates to zero
            (Requirement 4.1).
        InvalidSyntaxError: If an operator or node shape is not recognized
            (defensive; a well-formed AST never triggers this).
    """
    with localcontext(_CONTEXT) as ctx:
        # Clear the inexact flag so that, after the walk, it tells us whether any
        # operation lost significance (i.e. produced a non-terminating expansion
        # that had to be rounded to the working precision). An exact result keeps
        # the flag clear no matter how many significant digits it carries.
        ctx.clear_flags()
        raw = _eval(node, ctx)
        was_inexact = bool(ctx.flags[Inexact])
        return _finalize(raw, was_inexact, ctx)


def _eval(node: Node, ctx: Context) -> Decimal:
    """Recursively evaluate ``node`` under the active context ``ctx``."""
    if isinstance(node, NumberNode):
        # The operand is already an exact Decimal built from its lexeme by the
        # parser; re-apply the context so it participates at working precision.
        return +node.value

    if isinstance(node, UnaryOpNode):
        operand = _eval(node.operand, ctx)
        if node.op == "-":
            return ctx.minus(operand)
        raise InvalidSyntaxError(  # pragma: no cover - defensive
            message=f"Unsupported unary operator '{node.op}'."
        )

    if isinstance(node, BinaryOpNode):
        left = _eval(node.left, ctx)
        right = _eval(node.right, ctx)
        return _apply_binary(node.op, left, right, ctx)

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
    * A base/exponent combination with no real value (e.g. a negative base with
      a fractional exponent) is an invalid operation and surfaces as
      :class:`InvalidSyntaxError` rather than leaking a decimal ``NaN``.

    A non-representable-but-valid power (irrational result) is left to
    :func:`_finalize`, which rounds it to >=10 significant digits.
    """
    if base == 0 and exponent < 0:
        raise DivisionByZeroError()
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


def evaluate_ast(node: Node) -> Decimal:
    """Alias for :func:`evaluate`.

    Provided for callers/tests that prefer an explicit ``evaluate_ast`` name to
    distinguish AST evaluation from the higher-level ``evaluate_expression``
    entry point (see :mod:`app.engine`).
    """
    return evaluate(node)


__all__ = ["evaluate", "evaluate_ast"]
