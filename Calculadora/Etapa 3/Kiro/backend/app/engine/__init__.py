"""The Evaluation_Engine package: the pure, HTTP-agnostic computation core.

This package is the arithmetic heart of the Backend_Service. It is composed of
three sequential stages that together turn a raw expression string into an exact
:class:`~decimal.Decimal` result:

    tokenizer -> parser -> evaluator

Each stage lives in its own module and depends only on the stage below it, so
the whole core stays free of HTTP concerns and is independently unit-testable
(Requirement 14.2). The transport/validation layers in :mod:`app.api` call into
this package through the single public entry point defined here.

Public entry point
------------------
:func:`evaluate_expression` is the supported way to evaluate an expression. It
wires the three stages together and lets any :class:`EvaluationError` subclass
propagate unchanged so the caller (the API layer) can map it to an
``ErrorResponse`` (design "Evaluation_Engine" / "Error Handling").

For convenience and testing, the useful lower-level names are re-exported here:
the staged functions (:func:`parse`, :func:`render`, :func:`evaluate`) and the
full :class:`EvaluationError` hierarchy.
"""

from __future__ import annotations

from decimal import Decimal

from .errors import (
    DivisionByZeroError,
    DomainError,
    EmptyExpressionError,
    EvaluationError,
    InvalidCharacterError,
    InvalidFunctionError,
    InvalidSyntaxError,
    UnbalancedParenthesesError,
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
from .tokenizer import tokenize


def evaluate_expression(expression: str, angle_mode: str = "radians") -> Decimal:
    """Tokenize, parse, and evaluate an arithmetic ``expression``.

    This is the single public entry point into the Evaluation_Engine. It runs
    the pure computation pipeline end to end:

    1. :func:`app.engine.parser.parse` tokenizes the raw string and builds a
       PEMDAS-structured AST (the parser tokenizes internally, so there is no
       separate tokenize call here).
    2. :func:`app.engine.evaluator.evaluate` walks that AST and computes an
       exact, normalized :class:`~decimal.Decimal` under the engine's decimal
       context. ``angle_mode`` is threaded through to the evaluator so the
       trigonometric functions interpret their arguments in the requested unit.

    Any failure in either stage surfaces as an :class:`EvaluationError`
    subclass, which is allowed to propagate to the caller unchanged; no error
    path ever returns a calculated result (Requirements 1.1, 4.x, 14.2). The
    Stage 2 scientific operations add :class:`DomainError` and
    :class:`InvalidFunctionError` to the set of propagated subclasses.

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
    """
    ast = parse(expression)
    return evaluate(ast, angle_mode)


__all__ = [
    # Public entry point.
    "evaluate_expression",
    # Staged functions, re-exported for convenience/testing.
    "tokenize",
    "parse",
    "render",
    "evaluate",
    # AST node types.
    "Node",
    "NumberNode",
    "UnaryOpNode",
    "BinaryOpNode",
    "ConstantNode",
    "FunctionNode",
    "RootNode",
    # Error hierarchy.
    "EvaluationError",
    "EmptyExpressionError",
    "InvalidCharacterError",
    "InvalidSyntaxError",
    "UnbalancedParenthesesError",
    "DivisionByZeroError",
    "DomainError",
    "InvalidFunctionError",
]
