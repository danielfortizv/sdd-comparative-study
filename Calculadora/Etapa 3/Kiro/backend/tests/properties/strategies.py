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
# ``render`` already serializes ConstantNode/FunctionNode/RootNode (task 20.1),
# so the scientific generators below reuse it unchanged.
# NOTE: we intentionally do NOT import app.engine.evaluator or
# app.engine.scientific -- the reference oracle below must be an INDEPENDENT
# implementation for Properties 1, 14, 16, 18 to be real cross-checks. The only
# thing we take from the engine are the AST node types and ``render``.
from app.engine.parser import (
    BinaryOpNode,
    ConstantNode,
    FunctionNode,
    NumberNode,
    RootNode,
    UnaryOpNode,
    render,
)

__all__ = [
    "PROPERTY_SETTINGS",
    "MAX_EXAMPLES",
    "render",
    "asts",
    "scientific_asts",
    "numbers",
    "decimal_literals",
    "reference_evaluate",
    "ReferenceError",
    "ReferenceDivisionByZero",
    "ReferenceDomainError",
    "expressions_with_invalid_character",
    "zero_divisor_expressions",
    "over_length_expressions",
    # Stage 2 in-domain scientific node generators.
    "constant_nodes",
    "function_nodes",
    "root_nodes",
    "trig_operands",
    "tan_safe_operands",
    "asin_acos_operands",
    "atan_operands",
    "log_operands",
    "sqrt_operands",
    # Stage 2 out-of-domain (DomainError) generators.
    "domain_error_expressions",
    "asin_acos_out_of_domain_expressions",
    "sqrt_negative_expressions",
    "even_root_negative_expressions",
    "zero_degree_root_expressions",
    "log_non_positive_expressions",
    "negative_base_fractional_exponent_expressions",
    "tan_singularity_expressions",
    # Stage 2 independent Decimal reference oracle.
    "REFERENCE_PI",
    "REFERENCE_E",
    "reference_constant",
    "reference_sin",
    "reference_cos",
    "reference_tan",
    "reference_asin",
    "reference_acos",
    "reference_atan",
    "reference_ln",
    "reference_log10",
    "reference_sqrt",
    "reference_nth_root",
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


class ReferenceDomainError(ReferenceError):
    """Raised by the independent oracle when a scientific operation is undefined.

    Mirrors the engine's :class:`~app.engine.errors.DomainError` *contract* (not
    its code): ``asin``/``acos`` outside ``[-1, 1]``, ``sqrt`` of a negative,
    even/ non-integer-degree root of a negative, a zero root degree,
    ``ln``/``log10`` of a non-positive value, and ``tan`` at an odd multiple of
    pi/2. Keeping an independent domain judgement here is what lets the oracle
    cross-check the engine's domain handling (Property 17) rather than echo it.
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
# Stage 2: in-domain operand strategies for scientific functions
# --------------------------------------------------------------------------- #
# Each strategy yields *Decimal* operands constrained to the function's real
# domain, so a FunctionNode/RootNode wrapping one of these always evaluates
# without a DomainError. They are built from string literals (never ``float``)
# to stay exact, and bounded so series/root convergence is fast and the >=10
# significant-digit contract is never at risk. Out-of-domain cases are covered
# separately by the DomainError generators further below (Property 17).

#: Bound for generic trig operands. Angles are modest Decimals in [-10, 10];
#: the engine range-reduces internally, so a small window exercises every
#: quadrant without generating unwieldy magnitudes.
_TRIG_BOUND = 10


def _signed(strategy: st.SearchStrategy[Decimal]) -> st.SearchStrategy[Decimal]:
    """Attach a random sign to a non-negative Decimal strategy."""
    return st.builds(
        lambda value, negative: -value if negative else value,
        strategy,
        st.booleans(),
    )


def _bounded_decimals(
    low: str, high: str, *, places: int = 6
) -> st.SearchStrategy[Decimal]:
    """Decimals in the closed interval ``[low, high]`` with ``places`` precision.

    Produced from integer "ticks" scaled by ``10**-places`` and built via
    ``Decimal(str)`` so the values stay exact and never touch ``float``.
    """
    scale = Decimal(10) ** places
    low_d = Decimal(low)
    high_d = Decimal(high)
    min_tick = int((low_d * scale).to_integral_value())
    max_tick = int((high_d * scale).to_integral_value())
    quantum = Decimal(1).scaleb(-places)
    return st.integers(min_value=min_tick, max_value=max_tick).map(
        lambda tick: (Decimal(tick) * quantum).quantize(quantum)
    )


def trig_operands() -> st.SearchStrategy[Decimal]:
    """In-domain operands for ``sin``/``cos`` (any bounded Decimal angle)."""
    return _bounded_decimals(str(-_TRIG_BOUND), str(_TRIG_BOUND))


def tan_safe_operands() -> st.SearchStrategy[Decimal]:
    """Operands for ``tan`` that stay comfortably away from its singularities.

    ``tan`` is undefined at odd multiples of pi/2 (radians). Rather than reason
    about where those land for a generated Decimal, we restrict ``tan`` operands
    to the open interval ``(-1.5, 1.5)`` radians: the nearest singularity is
    ``pi/2 ~ 1.5708``, so ``cos`` is comfortably non-zero across the whole range
    and the "valid" generator never hits the domain error. The singularity case
    is exercised on purpose by :func:`tan_singularity_expressions` (Property 17).
    """
    return _bounded_decimals("-1.5", "1.5")


def asin_acos_operands() -> st.SearchStrategy[Decimal]:
    """In-domain operands for ``asin``/``acos`` (the closed interval [-1, 1])."""
    return _bounded_decimals("-1", "1")


def atan_operands() -> st.SearchStrategy[Decimal]:
    """In-domain operands for ``atan`` (any bounded Decimal; domain is all reals)."""
    return _bounded_decimals(str(-_TRIG_BOUND), str(_TRIG_BOUND))


def log_operands() -> st.SearchStrategy[Decimal]:
    """Strictly-positive operands for ``ln``/``log10`` (the interval (0, 1000])."""
    return _bounded_decimals("0.000001", "1000")


def sqrt_operands() -> st.SearchStrategy[Decimal]:
    """Non-negative operands for ``sqrt`` (the interval [0, 1000])."""
    return _bounded_decimals("0", "1000")


#: Pairs each unary function name with the strategy producing its in-domain
#: Decimal operand. ``tan`` deliberately uses the singularity-avoiding strategy.
_FUNCTION_OPERANDS = {
    "sin": trig_operands,
    "cos": trig_operands,
    "tan": tan_safe_operands,
    "asin": asin_acos_operands,
    "acos": asin_acos_operands,
    "atan": atan_operands,
    "ln": log_operands,
    "log10": log_operands,
    "sqrt": sqrt_operands,
}


def constant_nodes() -> st.SearchStrategy[ConstantNode]:
    """A strategy of :class:`ConstantNode` leaves (``pi`` or ``e``)."""
    return st.sampled_from([ConstantNode("pi"), ConstantNode("e")])


def function_nodes() -> st.SearchStrategy[FunctionNode]:
    """A strategy of in-domain :class:`FunctionNode` calls.

    Each generated node pairs a function name with an operand drawn from that
    function's in-domain operand strategy, wrapped in a :class:`NumberNode`, so
    the node always evaluates without raising a domain error.
    """
    choices = [
        operand_strategy().map(
            lambda value, _name=name: FunctionNode(_name, NumberNode(value))
        )
        for name, operand_strategy in _FUNCTION_OPERANDS.items()
    ]
    return st.one_of(*choices)


def root_nodes() -> st.SearchStrategy[RootNode]:
    """A strategy of in-domain :class:`RootNode` ``root(radicand, degree)`` calls.

    Degrees are small positive integers (2..5). For an even degree the radicand
    is constrained non-negative (an even root of a negative has no real value);
    for an odd degree the radicand may carry either sign. Radicands are bounded
    so the ``exp(ln/n)`` root stays well inside the working precision.
    """
    radicand_magnitude = _bounded_decimals("0", "1000")

    def _build(degree: int, magnitude: Decimal, negative: bool) -> RootNode:
        radicand = -magnitude if (negative and degree % 2 == 1) else magnitude
        return RootNode(NumberNode(radicand), NumberNode(Decimal(degree)))

    return st.builds(
        _build,
        st.integers(min_value=2, max_value=5),
        radicand_magnitude,
        st.booleans(),
    )


# --------------------------------------------------------------------------- #
# Stage 2: recursive scientific AST strategy
# --------------------------------------------------------------------------- #
def scientific_asts(max_depth: int = _MAX_DEPTH) -> st.SearchStrategy:
    """A recursive strategy generating valid ASTs that include scientific nodes.

    This is a *separate* generator from :func:`asts` on purpose: widening the
    Stage 1 ``asts`` would destabilize the P1/P3 generators (which deliberately
    stay within exact, terminating arithmetic). ``scientific_asts`` instead
    builds trees that may contain constants, unary scientific functions, and
    n-th roots *as subtrees*, while keeping every tree in-domain so it evaluates
    without a :class:`~app.engine.errors.DomainError`.

    In-domain nesting is preserved by applying a function to an *already
    in-domain leaf operand* rather than to an arbitrary subtree (a nested
    ``ln`` of an arbitrary subtree could easily go non-positive). Additive,
    multiplicative, unary-minus, and (small positive integer) power combinators
    still compose arbitrary scientific/arithmetic subtrees, so a generated tree
    can look like ``sin(0.5) + 2 * root(8, 3)`` or ``-(pi ^ 2) / cos(1)``.

    Args:
        max_depth: Maximum recursion depth; ``0`` yields only leaves.

    Returns:
        A Hypothesis strategy producing ``Node`` values that evaluate in-domain.
    """
    # Leaves: plain numbers, named constants, in-domain function calls, and
    # in-domain roots. Each leaf is self-contained and evaluable on its own.
    leaves = st.one_of(numbers(), constant_nodes(), function_nodes(), root_nodes())

    def _extend(children: st.SearchStrategy) -> st.SearchStrategy:
        additive_multiplicative = st.builds(
            BinaryOpNode,
            st.sampled_from(["+", "-", "*"]),
            children,
            children,
        )
        division = st.builds(
            lambda left, right: BinaryOpNode("/", left, right),
            children,
            numbers(allow_zero=False),
        )
        power = st.builds(
            lambda base, exp: BinaryOpNode("^", base, exp),
            children,
            _exponents(),
        )
        unary = st.builds(lambda operand: UnaryOpNode("-", operand), children)
        return st.one_of(additive_multiplicative, division, power, unary)

    return st.recursive(leaves, _extend, max_leaves=max_depth * 2)


# --------------------------------------------------------------------------- #
# Stage 2: out-of-domain generators (Property 17, one per DomainError category)
# --------------------------------------------------------------------------- #
# Each strategy yields a *parseable* expression string the engine must reject
# with a DomainError (mapped to a 4xx by the API). They are rendered with the
# engine's ``render`` (or built directly) so they are guaranteed to tokenize and
# parse -- the rejection is a genuine *domain* rejection, not a syntax error.


def asin_acos_out_of_domain_expressions() -> st.SearchStrategy[str]:
    """``asin``/``acos`` of a value with ``|x| > 1`` (Requirement 17.8)."""
    out_of_range = _signed(_bounded_decimals("1.000001", "1000"))
    return st.builds(
        lambda name, value: render(FunctionNode(name, NumberNode(value))),
        st.sampled_from(["asin", "acos"]),
        out_of_range,
    )


def sqrt_negative_expressions() -> st.SearchStrategy[str]:
    """``sqrt`` of a strictly negative value (Requirement 18.8)."""
    negatives = _bounded_decimals("0.000001", "1000").map(lambda d: -d)
    return st.builds(
        lambda value: render(FunctionNode("sqrt", NumberNode(value))),
        negatives,
    )


def even_root_negative_expressions() -> st.SearchStrategy[str]:
    """Even-degree ``root`` of a strictly negative radicand (Requirement 18.8)."""
    negatives = _bounded_decimals("0.000001", "1000").map(lambda d: -d)
    even_degrees = st.sampled_from([2, 4, 6, 8]).map(lambda n: Decimal(n))
    return st.builds(
        lambda radicand, degree: render(
            RootNode(NumberNode(radicand), NumberNode(degree))
        ),
        negatives,
        even_degrees,
    )


def zero_degree_root_expressions() -> st.SearchStrategy[str]:
    """``root`` with a degree of zero (Requirement 18.10)."""
    radicands = _signed(_bounded_decimals("0", "1000"))
    return st.builds(
        lambda radicand: render(
            RootNode(NumberNode(radicand), NumberNode(Decimal(0)))
        ),
        radicands,
    )


def log_non_positive_expressions() -> st.SearchStrategy[str]:
    """``ln``/``log10`` of a non-positive value (<= 0) (Requirement 18.7)."""
    non_positive = st.one_of(
        st.just(Decimal(0)),
        _bounded_decimals("0.000001", "1000").map(lambda d: -d),
    )
    return st.builds(
        lambda name, value: render(FunctionNode(name, NumberNode(value))),
        st.sampled_from(["ln", "log10"]),
        non_positive,
    )


def negative_base_fractional_exponent_expressions() -> st.SearchStrategy[str]:
    """A negative base raised to a non-integer exponent (Requirement 18.9).

    Built directly as ``(-base) ^ exponent`` with a fractional exponent, which
    has no real value and must be rejected with a DomainError.
    """
    bases = _bounded_decimals("0.5", "100")
    # Non-integer exponents: an integer part plus a strictly fractional part.
    frac_exponents = _bounded_decimals("0.1", "5").filter(
        lambda d: d != d.to_integral_value()
    )
    return st.builds(
        lambda base, exponent: render(
            BinaryOpNode(
                "^",
                UnaryOpNode("-", NumberNode(base)),
                NumberNode(exponent),
            )
        ),
        bases,
        frac_exponents,
    )


def tan_singularity_expressions() -> st.SearchStrategy[str]:
    """``tan`` at an odd multiple of 90 degrees (Requirement 17.7).

    Returns ``tan(<odd-multiple-of-90>)`` strings meant to be evaluated with the
    engine in **degrees** mode, where the argument lands exactly on a tangent
    singularity (90, 270, -90, ...). In degrees the singularity is exact, which
    makes this a clean, deterministic domain-error case for Property 17.
    """
    odd_multiples = st.integers(min_value=-5, max_value=5).map(
        lambda k: Decimal(90 + 180 * k)
    )
    return st.builds(
        lambda angle: render(FunctionNode("tan", NumberNode(angle))),
        odd_multiples,
    )


def domain_error_expressions() -> st.SearchStrategy[str]:
    """Union of every out-of-domain generator (a one-stop Property 17 source).

    .. note::
       :func:`tan_singularity_expressions` is only a domain error in *degrees*
       mode; the P17 test should drive the tan case (or this union) with the
       engine configured for degrees. The other categories are domain errors in
       either angle mode.
    """
    return st.one_of(
        asin_acos_out_of_domain_expressions(),
        sqrt_negative_expressions(),
        even_root_negative_expressions(),
        zero_degree_root_expressions(),
        log_non_positive_expressions(),
        negative_base_fractional_exponent_expressions(),
        tan_singularity_expressions(),
    )


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
# Independent high-precision Decimal oracle for the scientific ops (P14/P16/P18)
# --------------------------------------------------------------------------- #
# These functions compute the *expected* scientific values with their own math,
# so agreement with ``app.engine.scientific`` is a real cross-check rather than
# a tautology. They deliberately do NOT import ``app.engine.scientific`` (nor
# ``math``/``float``). In particular:
#
#   * trig/inverse-trig use an INDEPENDENT Taylor/Maclaurin series with a simple
#     modulo-2*pi range reduction -- a different algorithm from the engine's
#     quadrant-octant reduction, so Property 14 compares two genuinely distinct
#     implementations;
#   * ln/log10/sqrt/nth_root use the ``Decimal`` built-ins (``.ln()``,
#     ``.log10()``, ``.sqrt()``, ``exp(ln/n)``) -- these are the canonical
#     correctly-rounded references for Property 16 and are independent of the
#     engine's Newton-refined implementation.
#
# All work runs in a localcontext with ~10 guard digits above the Stage 1
# precision so comparisons at >=10 significant digits are safe.

#: Guard-digit working precision for the oracle (Stage 1 precision + slack).
_ORACLE_PRECISION = _WORKING_PRECISION + 10
_ORACLE_CONTEXT = Context(prec=_ORACLE_PRECISION, rounding=ROUND_HALF_EVEN)

#: Independent high-precision literals for pi and e (>=50 significant digits).
#: Using literal constant *values* is fine (a constant is a constant); what must
#: be independent is the trig *algorithm*, which it is. These are kept here so
#: the oracle does not import ``app.engine.constants`` either.
REFERENCE_PI = Decimal(
    "3.14159265358979323846264338327950288419716939937510582097494459"
)
REFERENCE_E = Decimal(
    "2.71828182845904523536028747135266249775724709369995957496696763"
)

_ORACLE_RADIANS = "radians"
_ORACLE_DEGREES = "degrees"


def reference_constant(name: str) -> Decimal:
    """Independent reference value for a named constant (``pi`` or ``e``)."""
    with localcontext(_ORACLE_CONTEXT):
        if name == "pi":
            return +REFERENCE_PI
        if name == "e":
            return +REFERENCE_E
        raise ReferenceError(f"Unknown constant {name!r}.")


def _oracle_to_radians(value: Decimal, angle_mode: str) -> Decimal:
    """Interpret ``value`` under ``angle_mode`` and return radians."""
    if angle_mode == _ORACLE_DEGREES:
        return value * REFERENCE_PI / Decimal(180)
    return +value


def _oracle_from_radians(value: Decimal, angle_mode: str) -> Decimal:
    """Convert a radian ``value`` back into ``angle_mode`` units."""
    if angle_mode == _ORACLE_DEGREES:
        return value * Decimal(180) / REFERENCE_PI
    return +value


def _reduce_mod_two_pi(radians: Decimal) -> Decimal:
    """Reduce an angle into ``(-pi, pi]`` by subtracting an integer * 2*pi.

    A single exact Decimal remainder against ``2*pi`` -- a *different* strategy
    from the engine's pi/2 octant reduction, keeping this oracle independent.
    """
    two_pi = REFERENCE_PI * 2
    k = (radians / two_pi).to_integral_value(rounding=ROUND_HALF_EVEN)
    return radians - k * two_pi


def _series_sin(radians: Decimal) -> Decimal:
    """Independent Maclaurin series for sin after modulo-2*pi reduction.

    ``sin(x) = x - x^3/3! + x^5/5! - ...``; summation stops when a term stops
    affecting the running total at the oracle precision.
    """
    x = _reduce_mod_two_pi(radians)
    x_sq = x * x
    term = +x
    total = +x
    n = 1
    while True:
        term = term * (-x_sq) / (Decimal(2 * n) * Decimal(2 * n + 1))
        new_total = total + term
        if new_total == total:
            return total
        total = new_total
        n += 1


def _series_cos(radians: Decimal) -> Decimal:
    """Independent Maclaurin series for cos after modulo-2*pi reduction.

    ``cos(x) = 1 - x^2/2! + x^4/4! - ...``.
    """
    x = _reduce_mod_two_pi(radians)
    x_sq = x * x
    term = Decimal(1)
    total = Decimal(1)
    n = 1
    while True:
        term = term * (-x_sq) / (Decimal(2 * n - 1) * Decimal(2 * n))
        new_total = total + term
        if new_total == total:
            return total
        total = new_total
        n += 1


def reference_sin(x: Decimal, angle_mode: str = _ORACLE_RADIANS) -> Decimal:
    """Independent reference sine of ``x`` (interpreted in ``angle_mode``)."""
    with localcontext(_ORACLE_CONTEXT):
        return +_series_sin(_oracle_to_radians(x, angle_mode))


def reference_cos(x: Decimal, angle_mode: str = _ORACLE_RADIANS) -> Decimal:
    """Independent reference cosine of ``x`` (interpreted in ``angle_mode``)."""
    with localcontext(_ORACLE_CONTEXT):
        return +_series_cos(_oracle_to_radians(x, angle_mode))


def reference_tan(x: Decimal, angle_mode: str = _ORACLE_RADIANS) -> Decimal:
    """Independent reference tangent ``sin/cos`` (interpreted in ``angle_mode``).

    Raises :class:`ReferenceDomainError` when ``cos`` is effectively zero (an
    odd multiple of pi/2), matching the engine's singularity rejection.
    """
    with localcontext(_ORACLE_CONTEXT):
        radians = _oracle_to_radians(x, angle_mode)
        s = _series_sin(radians)
        c = _series_cos(radians)
        if abs(c) < Decimal(1).scaleb(-(_WORKING_PRECISION)):
            raise ReferenceDomainError("tangent is undefined at this angle.")
        return +(s / c)


def _series_atan(x: Decimal) -> Decimal:
    """atan in radians via an independent series with argument reduction.

    Uses ``atan(x) = pi/2 - atan(1/x)`` for ``|x| > 1`` and a half-angle
    reduction (``atan(y) = 2*atan(y/(1+sqrt(1+y^2)))``) to shrink the series
    argument for fast convergence, then ``atan(y) = y - y^3/3 + y^5/5 - ...``.
    """
    if x == 0:
        return Decimal(0)
    negative = x < 0
    y = abs(x)

    use_complement = y > 1
    if use_complement:
        y = Decimal(1) / y

    reductions = 0
    while y > Decimal("0.42"):
        y = y / (Decimal(1) + (Decimal(1) + y * y).sqrt())
        reductions += 1

    y_sq = y * y
    power = +y
    total = +y
    sign = Decimal(-1)
    n = 1
    while True:
        power = power * y_sq
        n += 2
        contribution = sign * power / Decimal(n)
        new_total = total + contribution
        if new_total == total:
            break
        total = new_total
        sign = -sign

    result = total * (Decimal(2) ** reductions)
    if use_complement:
        result = REFERENCE_PI / 2 - result
    if negative:
        result = -result
    return result


def reference_atan(x: Decimal, angle_mode: str = _ORACLE_RADIANS) -> Decimal:
    """Independent reference arctangent; result expressed in ``angle_mode``."""
    with localcontext(_ORACLE_CONTEXT):
        return +_oracle_from_radians(_series_atan(+x), angle_mode)


def reference_asin(x: Decimal, angle_mode: str = _ORACLE_RADIANS) -> Decimal:
    """Independent reference arcsine; result in ``angle_mode``.

    ``asin(x) = atan(x / sqrt(1 - x^2))`` with exact endpoints; requires
    ``-1 <= x <= 1`` and raises :class:`ReferenceDomainError` otherwise.
    """
    with localcontext(_ORACLE_CONTEXT):
        value = +x
        if value < -1 or value > 1:
            raise ReferenceDomainError("asin is undefined outside [-1, 1].")
        if value == 1:
            result = REFERENCE_PI / 2
        elif value == -1:
            result = -REFERENCE_PI / 2
        else:
            result = _series_atan(value / (Decimal(1) - value * value).sqrt())
        return +_oracle_from_radians(result, angle_mode)


def reference_acos(x: Decimal, angle_mode: str = _ORACLE_RADIANS) -> Decimal:
    """Independent reference arccosine ``pi/2 - asin(x)``; result in ``angle_mode``.

    Requires ``-1 <= x <= 1`` and raises :class:`ReferenceDomainError` otherwise.
    """
    with localcontext(_ORACLE_CONTEXT):
        value = +x
        if value < -1 or value > 1:
            raise ReferenceDomainError("acos is undefined outside [-1, 1].")
        # acos(x) = pi/2 - asin(x); at the endpoints asin(+1) = +pi/2 and
        # asin(-1) = -pi/2, so acos(+1) = 0 and acos(-1) = pi (matches the
        # engine fix for defect D-01 in docs/stage3-audit-log.md).
        if value == 1:
            asin_r = REFERENCE_PI / 2
        elif value == -1:
            asin_r = -REFERENCE_PI / 2
        else:
            asin_r = _series_atan(value / (Decimal(1) - value * value).sqrt())
        return +_oracle_from_radians(REFERENCE_PI / 2 - asin_r, angle_mode)


def reference_ln(x: Decimal) -> Decimal:
    """Independent reference natural log via ``Decimal.ln`` (requires x > 0)."""
    with localcontext(_ORACLE_CONTEXT):
        value = +x
        if value <= 0:
            raise ReferenceDomainError("ln is undefined for non-positive x.")
        return +value.ln()


def reference_log10(x: Decimal) -> Decimal:
    """Independent reference base-10 log via ``Decimal.log10`` (requires x > 0)."""
    with localcontext(_ORACLE_CONTEXT):
        value = +x
        if value <= 0:
            raise ReferenceDomainError("log10 is undefined for non-positive x.")
        return +value.log10()


def reference_sqrt(x: Decimal) -> Decimal:
    """Independent reference square root via ``Decimal.sqrt`` (requires x >= 0)."""
    with localcontext(_ORACLE_CONTEXT):
        value = +x
        if value < 0:
            raise ReferenceDomainError("sqrt is undefined for negative x.")
        return +value.sqrt()


def reference_nth_root(radicand: Decimal, degree: Decimal) -> Decimal:
    """Independent reference real ``degree``-th root via ``exp(ln(|x|)/n)``.

    Domain rules mirror the engine's contract: a zero degree, an even/ non-
    integer-degree root of a negative radicand are rejected with
    :class:`ReferenceDomainError`; an odd-integer degree of a negative radicand
    yields the negative real root.
    """
    with localcontext(_ORACLE_CONTEXT):
        n = +degree
        value = +radicand
        if n == 0:
            raise ReferenceDomainError("The root degree must be non-zero.")
        if value == 0:
            return Decimal(0)

        n_is_integer = n == n.to_integral_value()
        n_is_even_integer = n_is_integer and (int(n) % 2 == 0)
        n_is_odd_integer = n_is_integer and (int(n) % 2 != 0)

        if value < 0:
            if n_is_even_integer or not n_is_odd_integer:
                raise ReferenceDomainError(
                    "Even/non-integer root of a negative number is not real."
                )
            magnitude = (-value).ln() / n
            return +(-(magnitude.exp()))

        return +((value.ln() / n).exp())


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
