"""Decimal-native scientific operations for the Evaluation_Engine.

This module supplies the pure mathematical kernels the scientific evaluator
(Stage 2, task 22) dispatches to when it walks a
:class:`~app.engine.parser.FunctionNode` or :class:`~app.engine.parser.RootNode`.
It is a leaf of the pure computation core: it imports only
:data:`app.engine.constants.PI` and the engine error taxonomy, and it is
HTTP-agnostic.

Design contract
---------------
Every public helper takes :class:`~decimal.Decimal` operands and returns a
full-precision :class:`~decimal.Decimal` result. **No raw ``float`` and no
``math`` module ever appear in any calculation path** -- pi, the Taylor/Maclaurin
series, the angle conversions, and the power/root/log helpers are all pure
``Decimal`` (consistent with the ``product.md`` rule and Requirements 17.1-17.8,
18.1-18.11). The caller (the evaluator) is responsible for running the Stage 1
``_finalize``/rounding afterward, so these helpers deliberately return the raw
high-precision value and never normalize or round to the public >=10-digit
contract themselves.

Precision / guard-digit strategy
--------------------------------
The Stage 1 evaluator works at ``prec = 50`` under ``ROUND_HALF_EVEN``. Iterative
routines (series summation, Newton's method) and the chained identities
(``asin`` via ``atan`` via ``sqrt`` ...) can each shed a few units in the last
place. To guarantee the exposed result is correct to >=10 significant digits
*after* the evaluator finalizes (Requirements 17.6, 18.6), all work inside this
module runs in a :func:`~decimal.localcontext` at :data:`_WORKING_PRECISION`
(``50 + _GUARD_DIGITS``) -- i.e. ~15 guard digits above the Stage 1 precision.
The extra digits absorb accumulated rounding so the first 50 (and certainly the
first 10) digits the evaluator keeps are trustworthy.

Algorithms
----------
* **Degree<->radian** (Requirement 17.5): ``radians = degrees * pi / 180`` and
  ``degrees = radians * 180 / pi``, using the exact :data:`~app.engine.constants.PI`
  as the single source of truth.
* **sin / cos** (Requirements 17.1, 17.2): range-reduce the argument modulo
  ``2*pi`` and then into ``[-pi/4, pi/4]`` using quadrant identities; evaluate a
  Maclaurin series on the small reduced angle (where it converges fast) and
  reconstruct the original value from the quadrant. ``tan = sin / cos``
  (Requirement 17.3); a near-zero ``cos`` (odd multiple of ``pi/2``) raises
  :class:`~app.engine.errors.DomainError` (Requirement 17.7).
* **atan / asin / acos** (Requirement 17.4): ``atan`` via its Taylor series with
  the identity ``atan(x) = pi/2 - atan(1/x)`` for ``|x| > 1`` (and an argument
  halving to speed convergence near ``|x| = 1``); ``asin(x) = atan(x / sqrt(1 -
  x^2))`` with the exact endpoints ``asin(+-1) = +-pi/2``; ``acos(x) = pi/2 -
  asin(x)``. ``asin``/``acos`` require ``-1 <= x <= 1`` (Requirement 17.8).
* **powers / roots / logs** (Requirements 18.1-18.6): ``ln`` and ``log10`` via
  ``Decimal.ln`` / ``Decimal.log10``; ``sqrt`` via ``Decimal.sqrt``;
  :func:`nth_root` via sign handling plus ``exp(ln(|x|) / n)`` refined with a
  Newton step. Domain checks raise :class:`~app.engine.errors.DomainError`:
  ``sqrt`` and even-integer-degree roots require ``x >= 0`` (Requirement 18.8),
  the root degree must be non-zero (Requirement 18.10), ``ln``/``log10`` require
  ``x > 0`` (Requirement 18.7), and any non-finite result is rejected
  (Requirement 18.11).

Split of responsibility with the evaluator (task 22)
-----------------------------------------------------
This module owns trig, inverse-trig, log, ``sqrt``, ``nth_root`` and the angle
conversions. It intentionally does **not** own binary ``^``: the Stage 1
evaluator keeps its existing ``_power`` and task 22 extends that ``_power`` for
the negative-base/non-integer-exponent -> :class:`DomainError` case. A
:func:`power` helper is provided here for completeness/reuse, but the evaluator's
``^`` path is free to keep using its own guarded ``_power``.
"""

from __future__ import annotations

from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext

from .constants import PI
from .errors import DomainError

# --------------------------------------------------------------------------- #
# Precision configuration
# --------------------------------------------------------------------------- #
#: The Stage 1 evaluator's working precision. Mirrored here so this module's
#: guard-digit budget is expressed relative to the precision the exposed result
#: is ultimately finalized at (see :mod:`app.engine.evaluator`).
_STAGE1_PRECISION = 50

#: Guard digits added on top of the Stage 1 precision while computing inside
#: this module. Iterative series and chained identities can lose a few ULP each;
#: these extra digits absorb that so the first >=10 (indeed >=50) significant
#: digits the evaluator keeps are correct (Requirements 17.6, 18.6).
_GUARD_DIGITS = 15

#: Full working precision used by every routine in this module.
_WORKING_PRECISION = _STAGE1_PRECISION + _GUARD_DIGITS

#: The context all scientific routines run under: guarded precision, banker's
#: rounding (matching the Stage 1 evaluator's ``ROUND_HALF_EVEN``).
_CONTEXT = Context(prec=_WORKING_PRECISION, rounding=ROUND_HALF_EVEN)

#: Recognized angle-mode strings. The evaluator passes one of these through.
_RADIANS = "radians"
_DEGREES = "degrees"

#: Small integer constants as Decimals, reused throughout.
_ZERO = Decimal(0)
_ONE = Decimal(1)
_TWO = Decimal(2)


# --------------------------------------------------------------------------- #
# Internal high-precision constants (computed once at import, in-context)
# --------------------------------------------------------------------------- #
def _pi() -> Decimal:
    """Return pi re-applied at the working precision."""
    return +PI


def _two_pi() -> Decimal:
    return _pi() * _TWO


def _half_pi() -> Decimal:
    return _pi() / _TWO


def _quarter_pi() -> Decimal:
    return _pi() / Decimal(4)


# --------------------------------------------------------------------------- #
# Angle conversion (Requirement 17.5)
# --------------------------------------------------------------------------- #
def deg2rad(degrees: Decimal) -> Decimal:
    """Convert ``degrees`` to radians via exact Decimal pi: ``deg * pi / 180``."""
    with localcontext(_CONTEXT):
        return degrees * _pi() / Decimal(180)


def rad2deg(radians: Decimal) -> Decimal:
    """Convert ``radians`` to degrees via exact Decimal pi: ``rad * 180 / pi``."""
    with localcontext(_CONTEXT):
        return radians * Decimal(180) / _pi()


def _to_radians(value: Decimal, angle_mode: str) -> Decimal:
    """Interpret ``value`` in ``angle_mode`` and return it in radians."""
    if angle_mode == _DEGREES:
        return value * _pi() / Decimal(180)
    return +value


def _from_radians(value: Decimal, angle_mode: str) -> Decimal:
    """Convert a radian ``value`` back into ``angle_mode`` units."""
    if angle_mode == _DEGREES:
        return value * Decimal(180) / _pi()
    return +value


# --------------------------------------------------------------------------- #
# sin / cos / tan (Requirements 17.1, 17.2, 17.3, 17.7)
# --------------------------------------------------------------------------- #
def _sin_series(x: Decimal) -> Decimal:
    """Maclaurin series for sin on a small reduced angle ``x`` in [-pi/4, pi/4].

    ``sin(x) = x - x^3/3! + x^5/5! - ...``. Summation stops once a term no longer
    affects the running total at the working precision.
    """
    term = +x
    total = +x
    x_sq = x * x
    n = 1
    while term != _ZERO:
        # advance to the next term: multiply by -x^2 / ((2n)(2n+1))
        term = term * (-x_sq) / (Decimal(2 * n) * Decimal(2 * n + 1))
        new_total = total + term
        if new_total == total:
            break
        total = new_total
        n += 1
    return total


def _cos_series(x: Decimal) -> Decimal:
    """Maclaurin series for cos on a small reduced angle ``x`` in [-pi/4, pi/4].

    ``cos(x) = 1 - x^2/2! + x^4/4! - ...``.
    """
    term = +_ONE
    total = +_ONE
    x_sq = x * x
    n = 1
    while term != _ZERO:
        # advance to the next term: multiply by -x^2 / ((2n-1)(2n))
        term = term * (-x_sq) / (Decimal(2 * n - 1) * Decimal(2 * n))
        new_total = total + term
        if new_total == total:
            break
        total = new_total
        n += 1
    return total


def _reduce_to_octant(radians: Decimal) -> tuple[Decimal, int]:
    """Range-reduce ``radians`` to a small angle plus a quadrant index.

    Returns ``(r, k)`` where ``r`` lies in ``[-pi/4, pi/4]`` and ``k`` (0..3) is
    the quadrant of the original angle modulo ``2*pi``. The caller rebuilds
    sin/cos from ``r`` and ``k`` via the standard quadrant identities. Handles
    arbitrarily large and negative arguments because the reduction is a single
    Decimal remainder against ``pi/2`` with an integer quotient, all exact at the
    working precision.
    """
    half_pi = _half_pi()
    # Number of pi/2 steps, rounded to the nearest integer (exact Decimal work).
    quotient = (radians / half_pi).to_integral_value(rounding=ROUND_HALF_EVEN)
    remainder = radians - quotient * half_pi
    k = int(quotient) % 4
    return remainder, k


def _sin_cos(radians: Decimal) -> tuple[Decimal, Decimal]:
    """Return ``(sin(radians), cos(radians))`` for an angle already in radians."""
    r, k = _reduce_to_octant(radians)
    s = _sin_series(r)
    c = _cos_series(r)
    # Apply the quadrant rotation by k * (pi/2):
    #   k=0 -> ( s,  c)
    #   k=1 -> ( c, -s)
    #   k=2 -> (-s, -c)
    #   k=3 -> (-c,  s)
    if k == 0:
        return s, c
    if k == 1:
        return c, -s
    if k == 2:
        return -s, -c
    return -c, s


def sin(x: Decimal, angle_mode: str = _RADIANS) -> Decimal:
    """Sine of ``x`` (interpreted in ``angle_mode``). Requirement 17.1."""
    with localcontext(_CONTEXT):
        radians = _to_radians(x, angle_mode)
        s, _ = _sin_cos(radians)
        return +s


def cos(x: Decimal, angle_mode: str = _RADIANS) -> Decimal:
    """Cosine of ``x`` (interpreted in ``angle_mode``). Requirement 17.2."""
    with localcontext(_CONTEXT):
        radians = _to_radians(x, angle_mode)
        _, c = _sin_cos(radians)
        return +c


def tan(x: Decimal, angle_mode: str = _RADIANS) -> Decimal:
    """Tangent of ``x`` = ``sin/cos`` (Requirement 17.3).

    Raises :class:`DomainError` when ``x`` is an odd multiple of 90 deg / pi/2,
    detected as a ``cos`` whose magnitude is below a precision-aware threshold
    (Requirement 17.7).
    """
    with localcontext(_CONTEXT):
        radians = _to_radians(x, angle_mode)
        s, c = _sin_cos(radians)
        # Precision-aware singularity test: cos ~ 0 relative to the working
        # precision means we are at an odd multiple of pi/2 and tan diverges.
        if abs(c) < _singularity_threshold():
            raise DomainError(
                message="tangent is undefined at this angle."
            )
        return +(s / c)


def _singularity_threshold() -> Decimal:
    """A small Decimal threshold scaled to the working precision.

    A reduced-angle ``cos`` closer to zero than this is treated as a true
    singularity rather than a representable small value. Set well below the
    Stage 1 precision but above the guard-digit noise floor so legitimate values
    (``tan(0)=0``, ``tan(45 deg)=1``, ``tan(60 deg)=sqrt(3)``) are unaffected.
    """
    return Decimal(1).scaleb(-(_STAGE1_PRECISION + _GUARD_DIGITS // 2))


# --------------------------------------------------------------------------- #
# atan / asin / acos (Requirements 17.4, 17.8)
# --------------------------------------------------------------------------- #
def _atan_series(x: Decimal) -> Decimal:
    """Taylor series for atan on ``|x| <= ~0.42`` (fast convergence).

    ``atan(x) = x - x^3/3 + x^5/5 - ...``.
    """
    x_sq = x * x
    term = +x
    total = +x
    n = 1
    sign = -_ONE
    power = +x
    while True:
        power = power * x_sq
        n += 2
        term = power / Decimal(n)
        contribution = sign * term
        new_total = total + contribution
        if new_total == total:
            break
        total = new_total
        sign = -sign
    return total


def _atan_radians(x: Decimal) -> Decimal:
    """atan(x) in radians for any real ``x`` (Requirement 17.4).

    Uses ``atan(x) = pi/2 - atan(1/x)`` for ``|x| > 1`` to keep the argument
    small, then a half-angle reduction (``atan(y) = 2*atan(y/(1+sqrt(1+y^2)))``)
    to push the series argument below ~0.42 for fast, stable convergence.
    """
    if x == 0:
        return +_ZERO
    negative = x < 0
    y = abs(x)

    # Reduce large arguments via the reciprocal identity.
    use_complement = y > 1
    if use_complement:
        y = _ONE / y

    # Two half-angle reductions bring y well inside the fast-convergence region.
    reductions = 0
    while y > Decimal("0.42"):
        y = y / (_ONE + (_ONE + y * y).sqrt())
        reductions += 1

    result = _atan_series(y)
    result = result * (_TWO ** reductions)

    if use_complement:
        result = _half_pi() - result
    if negative:
        result = -result
    return result


def atan(x: Decimal, angle_mode: str = _RADIANS) -> Decimal:
    """Arctangent of ``x``; result expressed in ``angle_mode``. Requirement 17.4."""
    with localcontext(_CONTEXT):
        result = _atan_radians(+x)
        return +_from_radians(result, angle_mode)


def asin(x: Decimal, angle_mode: str = _RADIANS) -> Decimal:
    """Arcsine of ``x``; result in ``angle_mode``. Requirements 17.4, 17.8.

    Requires ``-1 <= x <= 1``; otherwise raises :class:`DomainError`.
    """
    with localcontext(_CONTEXT):
        value = +x
        if value < -_ONE or value > _ONE:
            raise DomainError(
                message="asin is undefined for arguments outside [-1, 1]."
            )
        if value == _ONE:
            result = _half_pi()
        elif value == -_ONE:
            result = -_half_pi()
        else:
            # asin(x) = atan(x / sqrt(1 - x^2))
            denom = (_ONE - value * value).sqrt()
            result = _atan_radians(value / denom)
        return +_from_radians(result, angle_mode)


def acos(x: Decimal, angle_mode: str = _RADIANS) -> Decimal:
    """Arccosine of ``x`` = ``pi/2 - asin(x)``; result in ``angle_mode``.

    Requires ``-1 <= x <= 1``; otherwise raises :class:`DomainError`
    (Requirements 17.4, 17.8).
    """
    with localcontext(_CONTEXT):
        value = +x
        if value < -_ONE or value > _ONE:
            raise DomainError(
                message="acos is undefined for arguments outside [-1, 1]."
            )
        if value == _ONE:
            asin_r = +_ZERO
        elif value == -_ONE:
            asin_r = -_half_pi()
        else:
            denom = (_ONE - value * value).sqrt()
            asin_r = _atan_radians(value / denom)
        result = _half_pi() - asin_r
        return +_from_radians(result, angle_mode)


# --------------------------------------------------------------------------- #
# logarithms / sqrt / roots / power (Requirements 18.1-18.11)
# --------------------------------------------------------------------------- #
def ln(x: Decimal) -> Decimal:
    """Natural logarithm of ``x`` (Requirement 18.5).

    Requires ``x > 0``; otherwise raises :class:`DomainError` (Requirement 18.7).
    """
    with localcontext(_CONTEXT):
        value = +x
        if value <= _ZERO:
            raise DomainError(
                message="Logarithm is undefined for non-positive arguments."
            )
        result = value.ln()
        return _reject_non_finite(result)


def log10(x: Decimal) -> Decimal:
    """Base-10 logarithm of ``x`` (Requirement 18.5).

    Requires ``x > 0``; otherwise raises :class:`DomainError` (Requirement 18.7).
    """
    with localcontext(_CONTEXT):
        value = +x
        if value <= _ZERO:
            raise DomainError(
                message="Logarithm is undefined for non-positive arguments."
            )
        result = value.log10()
        return _reject_non_finite(result)


def sqrt(x: Decimal) -> Decimal:
    """Square root of ``x`` (Requirement 18.2).

    Requires ``x >= 0``; otherwise raises :class:`DomainError` (Requirement 18.8).
    """
    with localcontext(_CONTEXT):
        value = +x
        if value < _ZERO:
            raise DomainError(
                message="Square root is undefined for negative numbers."
            )
        return _reject_non_finite(value.sqrt())


def nth_root(radicand: Decimal, degree: Decimal) -> Decimal:
    """Real ``degree``-th root of ``radicand`` (Requirement 18.3).

    Domain rules:

    * ``degree == 0`` -> :class:`DomainError` (Requirement 18.10).
    * an *even integer* ``degree`` with ``radicand < 0`` -> :class:`DomainError`
      (no real root, Requirement 18.8).
    * an *odd integer* ``degree`` with ``radicand < 0`` -> the negative real root
      (e.g. ``root(-8, 3) == -2``).
    * otherwise the positive real root of ``|radicand|``.

    Computed in Decimal via ``exp(ln(|x|) / n)`` and refined with a single
    Newton step so integer cases (``root(27, 3) == 3``, ``root(16, 4) == 2``)
    land exactly to the working precision. No ``float`` is used.
    """
    with localcontext(_CONTEXT):
        n = +degree
        value = +radicand

        if n == _ZERO:
            raise DomainError(message="The root degree must be non-zero.")

        if value == _ZERO:
            return +_ZERO

        n_is_integer = n == n.to_integral_value()
        n_is_even_integer = n_is_integer and (int(n) % 2 == 0)
        n_is_odd_integer = n_is_integer and (int(n) % 2 != 0)

        if value < _ZERO:
            if n_is_even_integer:
                raise DomainError(
                    message="Even root of a negative number is not real."
                )
            if not n_is_odd_integer:
                # Non-integer degree of a negative radicand has no real value.
                raise DomainError(
                    message="Even root of a negative number is not real."
                )
            # Odd integer degree: real root is the negative of the positive root.
            root = _positive_root(-value, n)
            return _reject_non_finite(-root)

        return _reject_non_finite(_positive_root(value, n))


def _positive_root(value: Decimal, n: Decimal) -> Decimal:
    """Compute the positive ``n``-th root of a strictly positive ``value``.

    Uses ``exp(ln(value) / n)`` for the initial estimate and, when ``n`` is a
    positive integer, refines it with one Newton iteration
    ``r <- r - (r^n - value) / (n * r^(n-1))`` to pin exact integer roots to
    full working precision.
    """
    estimate = (value.ln() / n).exp()

    if n == n.to_integral_value() and n > 0:
        n_int = int(n)
        # A couple of Newton refinements remove any residual series error.
        for _ in range(3):
            power = estimate ** (n_int - 1)
            estimate = estimate - (power * estimate - value) / (n * power)
    return +estimate


def power(base: Decimal, exponent: Decimal) -> Decimal:
    """Raise ``base`` to ``exponent`` in Decimal (Requirement 18.1).

    Mirrors the Stage 1 ``_power`` guards conceptually:

    * ``0`` to a negative exponent is a division by zero -> :class:`DomainError`.
    * a negative base with a non-integer exponent has no real value ->
      :class:`DomainError` (Requirement 18.9).
    * any non-finite result is rejected (Requirement 18.11).

    The evaluator's ``^`` path keeps its own guarded ``_power``; this helper is
    provided for reuse and symmetry.
    """
    with localcontext(_CONTEXT):
        b = +base
        e = +exponent
        if b == _ZERO and e < _ZERO:
            raise DomainError(
                message="Zero cannot be raised to a negative power."
            )
        if b < _ZERO and e != e.to_integral_value():
            raise DomainError(
                message="A negative base cannot be raised to a non-integer power."
            )
        return _reject_non_finite(b ** e)


def _reject_non_finite(value: Decimal) -> Decimal:
    """Return ``value`` unless it is NaN/Infinity, in which case raise DomainError.

    Requirement 18.11: a non-finite scientific result is never exposed.
    """
    if not value.is_finite():
        raise DomainError(
            message="The expression produced a non-finite result."
        )
    return +value


# --------------------------------------------------------------------------- #
# Dispatch helper for the evaluator (task 22)
# --------------------------------------------------------------------------- #
#: Unary scientific functions keyed by the name the parser's FunctionNode carries.
_UNARY_FUNCTIONS = {
    "sin": sin,
    "cos": cos,
    "tan": tan,
    "asin": asin,
    "acos": acos,
    "atan": atan,
    "ln": lambda x, angle_mode=_RADIANS: ln(x),
    "log10": lambda x, angle_mode=_RADIANS: log10(x),
    "sqrt": lambda x, angle_mode=_RADIANS: sqrt(x),
}

#: Functions whose argument/result are angle-mode sensitive (trig & inverse-trig).
_ANGLE_SENSITIVE = frozenset({"sin", "cos", "tan", "asin", "acos", "atan"})


def apply_function(name: str, operand: Decimal, angle_mode: str = _RADIANS) -> Decimal:
    """Dispatch a unary :class:`~app.engine.parser.FunctionNode` to its kernel.

    Args:
        name: The function identifier carried by the ``FunctionNode`` (one of
            ``sin, cos, tan, asin, acos, atan, ln, log10, sqrt``).
        operand: The already-evaluated :class:`~decimal.Decimal` argument.
        angle_mode: ``"radians"`` or ``"degrees"``; consulted only by the
            angle-sensitive trig / inverse-trig functions.

    Returns:
        The full-precision :class:`~decimal.Decimal` result (the evaluator
        finalizes/rounds it).

    Raises:
        DomainError: On any mathematical domain violation.
        KeyError: If ``name`` is not a known unary function (defensive; the
            parser only ever emits known names).
    """
    func = _UNARY_FUNCTIONS[name]
    if name in _ANGLE_SENSITIVE:
        return func(operand, angle_mode)
    return func(operand)


__all__ = [
    "deg2rad",
    "rad2deg",
    "sin",
    "cos",
    "tan",
    "asin",
    "acos",
    "atan",
    "ln",
    "log10",
    "sqrt",
    "nth_root",
    "power",
    "apply_function",
]
