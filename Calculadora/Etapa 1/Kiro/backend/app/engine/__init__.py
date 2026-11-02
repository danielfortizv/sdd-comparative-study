"""The Evaluation_Engine package: the pure, HTTP-agnostic computation core.

This package is the arithmetic heart of the Backend_Service. As of the Stage 4
RPN migration it is composed of four sequential stages that together turn a raw
expression string into an exact :class:`~decimal.Decimal` result:

    tokenizer -> parser -> rpn (Shunting Yard) -> rpn_evaluator (stack machine)

Each stage lives in its own module and depends only on the stage below it, so
the whole core stays free of HTTP concerns and is independently unit-testable
(Requirement 14.2). The transport/validation layers in :mod:`app.api` call into
this package through the single public entry point defined here.

Public entry point
------------------
:func:`evaluate_expression` is the supported way to evaluate an expression. It
wires the stages together -- parse the expression into an AST, linearize that
AST into a parenthesis-free Reverse Polish sequence with :func:`app.engine.rpn.to_rpn`,
and evaluate that sequence on a Decimal-only stack with
:func:`app.engine.rpn_evaluator.stack_evaluate` -- and lets any
:class:`EvaluationError` subclass (including the four RPN-specific errors)
propagate unchanged so the caller (the API layer) can map it to an
``ErrorResponse`` (design "Stage 4 Design (RPN Engine Migration)" ->
"``engine/__init__.py`` (EDIT) -- rewire the single entry point").

The legacy AST-walking :func:`evaluate` is no longer on the request path. It is
retained and re-exported purely as an independent reference oracle for the
result-parity property test (Requirements 36.5, 43.3): the test evaluates the
same AST both ways and asserts the results agree to >=10 significant digits.

For convenience and testing, the useful lower-level names are re-exported here:
the staged functions (:func:`parse`, :func:`render`, :func:`to_rpn`,
:func:`stack_evaluate`, and the oracle :func:`evaluate`), the RPN token model,
and the full :class:`EvaluationError` hierarchy.
"""

from __future__ import annotations

from decimal import Decimal

from .errors import (
    DivisionByZeroError,
    DomainError,
    EmptyExpressionError,
    EmptyStackError,
    EvaluationError,
    InvalidCharacterError,
    InvalidFunctionError,
    InvalidSyntaxError,
    StackUnderflowError,
    SurplusOperandsError,
    UnbalancedParenthesesError,
    UnprocessableTokenError,
)
from .evaluator import evaluate
from .parser import (
    BinaryOpNode,
    ConstantNode,
    FunctionNode,
    Node,
    NumberNode,
    RootNode,
    UnaryOpNode,
    parse,
    render,
)
from .rpn import (
    BinaryOp,
    Constant,
    Operand,
    RootOp,
    RpnToken,
    RpnTokenSequence,
    UnaryFunc,
    to_rpn,
)
from .rpn_evaluator import stack_evaluate
from .tokenizer import tokenize


def evaluate_expression(expression: str, angle_mode: str = "radians") -> Decimal:
    """Tokenize, parse, and evaluate an arithmetic ``expression``.

    This is the single public entry point into the Evaluation_Engine. As of the
    Stage 4 RPN migration it runs the pure computation pipeline end to end:

    1. :func:`app.engine.parser.parse` tokenizes the raw string and builds a
       PEMDAS-structured AST (the parser tokenizes internally, so there is no
       separate tokenize call here).
    2. :func:`app.engine.rpn.to_rpn` linearizes that AST into a
       parenthesis-free Reverse Polish (postfix) token sequence via a
       deterministic post-order traversal.
    3. :func:`app.engine.rpn_evaluator.stack_evaluate` evaluates that sequence
       on a Decimal-only Evaluation_Stack and returns an exact, normalized
       :class:`~decimal.Decimal` under the engine's decimal context.
       ``angle_mode`` is threaded through so the trigonometric functions
       interpret their arguments in the requested unit.

    Any failure in any stage surfaces as an :class:`EvaluationError` subclass,
    which is allowed to propagate to the caller unchanged; no error path ever
    returns a calculated result (Requirements 1.1, 4.x, 14.2). The Stage 2
    scientific operations add :class:`DomainError` and
    :class:`InvalidFunctionError`, and the Stage 4 stack machine adds
    :class:`StackUnderflowError`, :class:`SurplusOperandsError`,
    :class:`EmptyStackError`, and :class:`UnprocessableTokenError` to the set of
    propagated subclasses.

    The legacy AST-walking :func:`evaluate` is intentionally *not* called here;
    it is retained only as the independent reference oracle for the result
    parity property (Requirements 36.5, 43.3).

    Args:
        expression: The raw arithmetic expression string.
        angle_mode: The unit used to interpret trigonometric arguments, either
            ``"radians"`` or ``"degrees"``. Defaults to ``"radians"`` so callers
            that omit it keep the Stage 1 / radians behavior (Requirement 24.3).

    Returns:
        The evaluated result as a :class:`~decimal.Decimal`, computed under
        PEMDAS with decimal precision (Requirement 1.1).

    Raises:
        EmptyExpressionError: If ``expression`` is empty or only whitespace.
        InvalidCharacterError: If ``expression`` contains a disallowed character.
        InvalidSyntaxError: On an invalid operator sequence or malformed number.
        UnbalancedParenthesesError: On an unclosed or unmatched parenthesis.
        DivisionByZeroError: If a divisor subexpression evaluates to zero.
        DomainError: If a scientific operation violates its mathematical domain.
        InvalidFunctionError: If the expression names an unknown function.
        StackUnderflowError: If an RPN operator lacks enough operands.
        SurplusOperandsError: If the RPN sequence leaves >1 value on the stack.
        EmptyStackError: If the RPN sequence leaves 0 values on the stack.
        UnprocessableTokenError: If an RPN token cannot be processed.
    """
    ast = parse(expression)
    rpn = to_rpn(ast)
    return stack_evaluate(rpn, angle_mode)


__all__ = [
    # Public entry point.
    "evaluate_expression",
    # Staged functions, re-exported for convenience/testing.
    "tokenize",
    "parse",
    "render",
    "to_rpn",
    "stack_evaluate",
    # Reference oracle (test-only; no longer on the request path).
    "evaluate",
    # AST node types.
    "Node",
    "NumberNode",
    "UnaryOpNode",
    "BinaryOpNode",
    "ConstantNode",
    "FunctionNode",
    "RootNode",
    # RPN token model.
    "RpnToken",
    "RpnTokenSequence",
    "Operand",
    "Constant",
    "BinaryOp",
    "UnaryFunc",
    "RootOp",
    # Error hierarchy.
    "EvaluationError",
    "EmptyExpressionError",
    "InvalidCharacterError",
    "InvalidSyntaxError",
    "UnbalancedParenthesesError",
    "DivisionByZeroError",
    "DomainError",
    "InvalidFunctionError",
    "StackUnderflowError",
    "SurplusOperandsError",
    "EmptyStackError",
    "UnprocessableTokenError",
]
