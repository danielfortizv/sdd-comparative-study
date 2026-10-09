"""Evaluation_Engine error hierarchy.

All domain errors raised by the tokenizer, parser, and evaluator derive from a
common :class:`EvaluationError` base that carries a machine-readable ``kind`` and
a human-readable ``message``. The API layer maps each subclass to a 4xx
``ErrorResponse`` (see design "Error Handling"). No error path ever returns a
calculated result.

Taxonomy (design Error Handling table):

======================  ==================================================  ===========
Error class             Trigger                                             Requirement
======================  ==================================================  ===========
EmptyExpressionError    Empty or whitespace-only expression                 4.5
InvalidCharacterError   Character outside ``[0-9. +-*/^()]``                4.4
InvalidSyntaxError      Invalid operator sequence / malformed structure     4.2
UnbalancedParenthesesE. Unclosed / unmatched parenthesis                    4.3
DivisionByZeroError     Divisor subexpression evaluates to zero             4.1
======================  ==================================================  ===========
"""

from __future__ import annotations


class EvaluationError(Exception):
    """Base class for every Evaluation_Engine domain error.

    Attributes:
        kind: A stable, machine-readable identifier for the error category
            (e.g. ``"empty_expression"``). Used by the API layer for mapping
            and by tests for unambiguous assertions.
        message: A descriptive, human-readable message suitable for surfacing
            to the User in an ``ErrorResponse``.
    """

    #: Machine-readable category identifier. Overridden by each subclass.
    kind: str = "evaluation_error"

    def __init__(self, message: str, *, kind: str | None = None) -> None:
        self.message = message
        if kind is not None:
            self.kind = kind
        super().__init__(message)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


class EmptyExpressionError(EvaluationError):
    """Raised when the expression is empty or contains only whitespace.

    Requirement 4.5.
    """

    kind = "empty_expression"

    def __init__(self, message: str = "No expression was provided.") -> None:
        super().__init__(message)


class InvalidCharacterError(EvaluationError):
    """Raised when the expression contains a character outside the allowed set.

    Allowed characters are digits, a decimal point, the operators ``+ - * / ^``,
    parentheses, and insignificant whitespace. Requirement 4.4.
    """

    kind = "invalid_character"

    def __init__(
        self,
        message: str | None = None,
        *,
        character: str | None = None,
        position: int | None = None,
    ) -> None:
        self.character = character
        self.position = position
        if message is None:
            if character is not None and position is not None:
                message = f"Invalid character '{character}' at position {position}."
            else:
                message = "The expression contains an invalid character."
        super().__init__(message)


class InvalidSyntaxError(EvaluationError):
    """Raised on an invalid operator sequence or otherwise malformed structure.

    Requirement 4.2.
    """

    kind = "invalid_syntax"

    def __init__(
        self,
        message: str | None = None,
        *,
        position: int | None = None,
    ) -> None:
        self.position = position
        if message is None:
            if position is not None:
                message = f"Invalid operator sequence near position {position}."
            else:
                message = "The expression contains an invalid operator sequence."
        super().__init__(message)


class UnbalancedParenthesesError(EvaluationError):
    """Raised on an unclosed or unmatched parenthesis.

    Requirement 4.3.
    """

    kind = "unbalanced_parentheses"

    def __init__(
        self,
        message: str | None = None,
        *,
        position: int | None = None,
    ) -> None:
        self.position = position
        if message is None:
            if position is not None:
                message = f"Unclosed parenthesis at position {position}."
            else:
                message = "The expression contains unbalanced parentheses."
        super().__init__(message)


class DivisionByZeroError(EvaluationError):
    """Raised when a divisor subexpression evaluates to zero.

    Requirement 4.1.
    """

    kind = "division_by_zero"

    def __init__(self, message: str = "Division by zero is not allowed.") -> None:
        super().__init__(message)


__all__ = [
    "EvaluationError",
    "EmptyExpressionError",
    "InvalidCharacterError",
    "InvalidSyntaxError",
    "UnbalancedParenthesesError",
    "DivisionByZeroError",
]
