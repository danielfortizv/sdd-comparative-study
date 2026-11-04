"""Stack-based Stack_Evaluator for a linearized RPN_Token_Sequence.

This module is the Stage 4 execution engine of the Evaluation_Engine migration:
it evaluates the parenthesis-free Reverse Polish (postfix) token sequence
produced by :func:`app.engine.rpn.to_rpn` on a Decimal-only Evaluation_Stack. It
is the fifth and final member of the pure computation core
(tokenizer -> parser -> rpn -> rpn_evaluator) and is HTTP-agnostic.

Design highlights (design "Stage 4 Design (RPN Engine Migration)" ->
"``engine/rpn_evaluator.py`` (NEW) -- the Stack_Evaluator"):

* **Decimal-only stack** (Requirement 36.6): every value pushed is a
  :class:`~decimal.Decimal`; nothing is ever converted to ``float``. The whole
  walk runs inside ``with localcontext(_CONTEXT)`` -- the *same* module-level
  context the Stage 1 :func:`app.engine.evaluator.evaluate` uses -- so arithmetic
  precision, rounding, and the ``Inexact`` flag behave identically.
* **Operand / Constant** tokens push a value in sequence order. A
  :class:`~app.engine.rpn.Constant` pushes its exact high-precision
  :class:`~decimal.Decimal` from the unchanged :mod:`app.engine.constants`
  (>=10 -- indeed >=50 -- significant digits; Requirements 36.1, 37.4).
  Recalled Memory_Register values arrive as ordinary numeric
  :class:`~app.engine.rpn.Operand` tokens and are pushed like any other operand
  with their full decimal value (Requirement 37.5).
* **BinaryOp** pops two operands -- **first popped = right, second popped =
  left** -- and applies ``+ - * / ^`` via the reused
  :func:`app.engine.evaluator._apply_binary`, which carries the Stage 1
  division-by-zero and ``_power`` domain/overflow rules. This pop order pins
  non-commutative ``-``, ``/``, ``^`` (``8 3 -`` -> 5, ``2 3 ^`` -> 8;
  Requirement 36.2).
* **UnaryFunc** pops one operand and applies the **unchanged**
  :mod:`app.engine.scientific` kernel under the active ``angle_mode`` (trig /
  inverse-trig / ``ln`` / ``log10`` / ``sqrt``); unary ``neg`` negates via
  ``ctx.minus`` (Requirements 36.3, 37.1, 37.2).
* **RootOp** pops two -- **first popped = degree, second popped = radicand** --
  and applies the same :func:`app.engine.scientific.nth_root` computation as the
  Stage 1 ``RootNode`` path (Requirement 37.3).
* **Finalization** (Requirements 36.4, 36.7): the single remaining stack value
  is returned through the *shared* :func:`app.engine.evaluator._finalize`, so a
  terminating result is normalized and a non-terminating result is rounded to
  >=10 significant digits with ``ROUND_HALF_EVEN`` -- exactly as in Stage 1/2.
  Reusing ``_CONTEXT`` / ``_apply_binary`` / ``_finalize`` and the unchanged
  kernels is what guarantees **pre-migration result parity**: any expression
  that produced a valid result under the infix engine returns an equal result to
  >=10 significant digits (Requirements 36.5, 43.3).

Defensive error taxonomy (all four are internal invariants with a well-formed
parser, but are raised, mapped to 4xx, and tested per Requirements 38 / 41.3):

* :class:`~app.engine.errors.StackUnderflowError` -- an operator needs more
  operands than the stack holds (Requirements 36.8, 37.7, 38.1).
* :class:`~app.engine.errors.SurplusOperandsError` -- more than one value
  remains after the whole sequence is consumed (Requirements 36.9, 38.2).
* :class:`~app.engine.errors.EmptyStackError` -- zero values remain after
  consumption (Requirement 38.3).
* :class:`~app.engine.errors.UnprocessableTokenError` -- a token is neither a
  valid operand nor a supported operator/function (Requirement 38.4).

A :class:`~app.engine.errors.DomainError` raised by any kernel (out-of-domain or
non-finite operand) propagates unchanged -> 4xx, never a result (Requirement
37.6, reusing the Stage 2 behavior).
"""

from __future__ import annotations

from decimal import Decimal, Inexact, localcontext

from . import scientific  # noqa: F401 - imported as module for dispatch
from .constants import constant_value
from .errors import (
    EmptyStackError,
    StackUnderflowError,
    SurplusOperandsError,
    UnprocessableTokenError,
)
from .evaluator import _CONTEXT, _apply_binary, _finalize
from .rpn import (
    BinaryOp,
    Constant,
    Operand,
    RootOp,
    RpnTokenSequence,
    UnaryFunc,
)

#: Default angle mode, mirroring the Stage 1/2 evaluator. Only angle-sensitive
#: trig / inverse-trig :class:`~app.engine.rpn.UnaryFunc` tokens consult it
#: (Requirements 17.9, 24.3); every other token ignores it entirely.
_DEFAULT_ANGLE_MODE = "radians"


def stack_evaluate(
    seq: RpnTokenSequence, angle_mode: str = _DEFAULT_ANGLE_MODE
) -> Decimal:
    """Evaluate an RPN_Token_Sequence on a Decimal-only Evaluation_Stack.

    Walks ``seq`` left to right, maintaining an Evaluation_Stack of
    :class:`~decimal.Decimal` values. Operand/constant tokens push a value;
    operator/function tokens pop their operands, compute via the reused Stage
    1/2 kernels, and push the result. The entire walk runs inside a copy of the
    shared module-level decimal context so the caller's ambient context is never
    mutated and precision/rounding match the infix engine exactly.

    Pop-order convention (pins non-commutative operand order):

    * :class:`~app.engine.rpn.BinaryOp`: **first popped = right, second popped =
      left** (Requirement 36.2).
    * :class:`~app.engine.rpn.RootOp`: **first popped = degree, second popped =
      radicand** (Requirement 37.3).

    Args:
        seq: The parenthesis-free postfix token sequence from
            :func:`app.engine.rpn.to_rpn`.
        angle_mode: ``"radians"`` (default) or ``"degrees"``; consulted only by
            angle-sensitive trig / inverse-trig ``UnaryFunc`` tokens
            (Requirements 17.9, 24.3).

    Returns:
        The single remaining stack value, normalized/rounded through the shared
        :func:`app.engine.evaluator._finalize` (Requirements 36.4, 36.7).

    Raises:
        StackUnderflowError: An operator token needs more operands than the
            stack holds (Requirements 36.8, 37.7, 38.1).
        SurplusOperandsError: More than one value remains after the whole
            sequence is consumed (Requirements 36.9, 38.2).
        EmptyStackError: Zero values remain after consumption (Requirement 38.3).
        UnprocessableTokenError: A token is neither a valid operand nor a
            supported operator/function (Requirement 38.4).
        DivisionByZeroError: A ``/`` operand's divisor is zero, or ``0 ^ neg``
            (reused Stage 1 behavior, Requirement 4.1).
        DomainError: A kernel rejects an out-of-domain or non-finite operand
            (Requirement 37.6).
    """
    with localcontext(_CONTEXT) as ctx:
        # Clear the inexact flag so that, after the walk, it reports whether any
        # operation lost significance and had to be rounded to working
        # precision -- exactly the discriminator _finalize uses (mirrors
        # evaluator.evaluate()).
        ctx.clear_flags()

        stack: list[Decimal] = []

        for token in seq:
            if isinstance(token, Operand):
                # A numeric operand (including a recalled Memory_Register value)
                # is pushed verbatim; re-apply the context so it participates at
                # working precision, just like NumberNode in the infix engine
                # (Requirements 36.1, 37.5).
                stack.append(+token.value)

            elif isinstance(token, Constant):
                # Resolve pi / e to their exact high-precision Decimal and
                # re-apply the context, mirroring the infix ConstantNode path
                # (Requirements 36.1, 37.4).
                stack.append(+constant_value(token.name))

            elif isinstance(token, BinaryOp):
                # first popped = right, second popped = left (Requirement 36.2).
                right = _pop(stack, operator=token.symbol)
                left = _pop(stack, operator=token.symbol)
                stack.append(_apply_binary(token.symbol, left, right, ctx))

            elif isinstance(token, UnaryFunc):
                operand = _pop(stack, operator=token.name)
                stack.append(_apply_unary(token.name, operand, ctx, angle_mode))

            elif isinstance(token, RootOp):
                # first popped = degree, second popped = radicand (Req 37.3).
                degree = _pop(stack, operator="root")
                radicand = _pop(stack, operator="root")
                result = scientific.nth_root(radicand, degree)
                stack.append(+result)

            else:
                # A token that is neither a valid operand nor a supported
                # operator/function. Defensive: a well-formed to_rpn never emits
                # such a token (Requirement 38.4).
                raise UnprocessableTokenError(token=repr(token))

        was_inexact = bool(ctx.flags[Inexact])
        return _finalize(_single_result(stack), was_inexact, ctx)


def _pop(stack: list[Decimal], *, operator: str) -> Decimal:
    """Pop one value, or raise :class:`StackUnderflowError` naming ``operator``.

    Defensive internal invariant: a well-formed RPN_Token_Sequence always has
    enough operands for each operator (Requirements 36.8, 37.7, 38.1).
    """
    if not stack:
        raise StackUnderflowError(operator=operator)
    return stack.pop()


def _apply_unary(
    name: str, operand: Decimal, ctx, angle_mode: str
) -> Decimal:
    """Apply a :class:`~app.engine.rpn.UnaryFunc` kernel to ``operand``.

    ``neg`` negates via the active context (mirroring the infix
    ``UnaryOpNode("-")`` path); every other name dispatches to the unchanged
    :func:`app.engine.scientific.apply_function` kernel under ``angle_mode``, with
    the full-precision result re-applied via unary plus exactly as the infix
    ``FunctionNode`` path does (Requirements 36.3, 37.1, 37.2).
    """
    if name == "neg":
        return ctx.minus(operand)
    result = scientific.apply_function(name, operand, angle_mode)
    return +result


def _single_result(stack: list[Decimal]) -> Decimal:
    """Return the sole stack value, or raise the appropriate RPN error.

    Exactly one value must remain after the whole sequence is consumed. Zero
    values -> :class:`EmptyStackError` (Requirement 38.3); more than one ->
    :class:`SurplusOperandsError` naming the count (Requirements 36.9, 38.2).
    Both are defensive invariants with a well-formed parser.
    """
    if not stack:
        raise EmptyStackError()
    if len(stack) > 1:
        raise SurplusOperandsError(count=len(stack))
    return stack[0]


__all__ = ["stack_evaluate"]
