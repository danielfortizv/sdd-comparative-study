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
    EmptyExpressionError,
    EvaluationError,
    InvalidCharacterError,
    InvalidSyntaxError,
    UnbalancedParenthesesError,
)
from .evaluator import evaluate
from .parser import (
    BinaryOpNode,
    Node,
    NumberNode,
    UnaryOpNode,
    parse,
    render,
)
from .tokenizer import tokenize


def evaluate_expression(expression: str) -> Decimal:
    """Tokenize, parse, and evaluate an arithmetic ``expression``.

    This is the single public entry point into the Evaluation_Engine. It runs
    the pure computation pipeline end to end:

    1. :func:`app.engine.parser.parse` tokenizes the raw string and builds a
       PEMDAS-structured AST (the parser tokenizes internally, so there is no
       separate tokenize call here).
    2. :func:`app.engine.evaluator.evaluate` walks that AST and computes an
       exact, normalized :class:`~decimal.Decimal` under the engine's decimal
       context.

    Any failure in either stage surfaces as an :class:`EvaluationError`
    subclass, which is allowed to propagate to the caller unchanged; no error
    path ever returns a calculated result (Requirements 1.1, 4.x, 14.2).

    Args:
        expression: The raw arithmetic expression string.

    Returns:
        The evaluated result as a :class:`~decimal.Decimal`, computed under
        PEMDAS with decimal precision (Requirement 1.1).

    Raises:
        EmptyExpressionError: If ``expression`` is empty or only whitespace.
        InvalidCharacterError: If ``expression`` contains a disallowed character.
        InvalidSyntaxError: On an invalid operator sequence or malformed number.
        UnbalancedParenthesesError: On an unclosed or unmatched parenthesis.
        DivisionByZeroError: If a divisor subexpression evaluates to zero.
    """
    ast = parse(expression)
    return evaluate(ast)


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
    # Error hierarchy.
    "EvaluationError",
    "EmptyExpressionError",
    "InvalidCharacterError",
    "InvalidSyntaxError",
    "UnbalancedParenthesesError",
    "DivisionByZeroError",
]
