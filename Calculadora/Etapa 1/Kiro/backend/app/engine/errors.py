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
DomainError             Mathematical domain violation (trig/root/log/...)   17.7, 17.8,
                                                                            18.7-18.11,
                                                                            24.8
InvalidFunctionError    Unrecognized identifier / function name             24.1 path
StackUnderflowError     RPN operator needs more operands than available     36.8, 37.7,
                                                                            38.1
SurplusOperandsError    RPN sequence leaves >1 value on the stack           36.9, 38.2
EmptyStackError         RPN sequence leaves 0 values on the stack           38.3
UnprocessableTokenError RPN token is neither a valid operand nor operator   38.4
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


class DomainError(EvaluationError):
    """Raised when a scientific operation violates its mathematical domain.

    Covers every Requirement 17/18 domain violation surfaced by the scientific
    evaluator: ``asin``/``acos`` of an argument outside ``[-1, 1]``, ``tan`` at a
    singularity, ``sqrt``/even-root of a negative number, an n-th root of degree
    zero, ``ln``/``log10`` of a non-positive argument, a negative base raised to a
    non-integer exponent, and any power/root/log producing a non-finite result.
    Always surfaced as a 4xx ``ErrorResponse`` and never a calculated result.

    Requirements 17.7, 17.8, 18.7, 18.8, 18.9, 18.10, 18.11, 24.8.
    """

    kind = "domain_error"

    def __init__(
        self,
        message: str | None = None,
    ) -> None:
        if message is None:
            message = "The expression contains a mathematical domain error."
        super().__init__(message)


class InvalidFunctionError(EvaluationError):
    """Raised when the expression contains an unrecognized identifier/function.

    The tokenizer/parser raises this for any identifier run that does not match a
    known function name (``sin``, ``cos``, ``tan``, ``asin``, ``acos``, ``atan``,
    ``ln``, ``log10``, ``sqrt``, ``root``) or constant (``pi``, ``e``). The
    message names the unknown identifier and, when available, its position,
    mirroring :class:`InvalidCharacterError`. Supports the Requirement 24.1 error
    path.
    """

    kind = "invalid_function"

    def __init__(
        self,
        message: str | None = None,
        *,
        name: str | None = None,
        position: int | None = None,
    ) -> None:
        self.name = name
        self.position = position
        if message is None:
            if name is not None and position is not None:
                message = f"Unknown function or name '{name}' at position {position}."
            elif name is not None:
                message = f"Unknown function or name '{name}'."
            else:
                message = "The expression contains an unknown function or name."
        super().__init__(message)


class StackUnderflowError(EvaluationError):
    """Raised when an RPN operator needs more operands than the stack holds.

    During stack evaluation of a linearized (Reverse Polish) token sequence, an
    operator or function token requires one or two operands to be present on the
    Evaluation_Stack. When fewer values are available, the operation cannot be
    satisfied and this error is raised, naming the offending operator. With a
    well-formed parser this is a defensive internal invariant, but it is still
    raised, mapped to a 4xx ``ErrorResponse``, and tested.

    Requirements 36.8, 37.7, 38.1.
    """

    kind = "stack_underflow"

    def __init__(
        self,
        message: str | None = None,
        *,
        operator: str | None = None,
    ) -> None:
        self.operator = operator
        if message is None:
            if operator is not None:
                message = (
                    f"Operator '{operator}' does not have enough operands "
                    "to evaluate."
                )
            else:
                message = "An operator does not have enough operands to evaluate."
        super().__init__(message)


class SurplusOperandsError(EvaluationError):
    """Raised when the RPN sequence leaves more than one value on the stack.

    After the entire token sequence has been consumed, exactly one value must
    remain on the Evaluation_Stack. When more than one value remains, the
    expression was under-specified and this error is raised, naming the count of
    values that remained. With a well-formed parser this is a defensive internal
    invariant, but it is still raised, mapped to a 4xx ``ErrorResponse``, and
    tested.

    Requirements 36.9, 38.2.
    """

    kind = "surplus_operands"

    def __init__(
        self,
        message: str | None = None,
        *,
        count: int | None = None,
    ) -> None:
        self.count = count
        if message is None:
            if count is not None:
                message = (
                    f"The expression left {count} values on the stack; "
                    "exactly one was expected."
                )
            else:
                message = (
                    "The expression left more than one value on the stack."
                )
        super().__init__(message)


class EmptyStackError(EvaluationError):
    """Raised when the RPN sequence leaves zero values on the stack.

    After the entire token sequence has been consumed, exactly one value must
    remain on the Evaluation_Stack. When no values remain, there is no result to
    return and this error is raised. With a well-formed parser this is a
    defensive internal invariant, but it is still raised, mapped to a 4xx
    ``ErrorResponse``, and tested.

    Requirement 38.3.
    """

    kind = "empty_stack"

    def __init__(
        self,
        message: str = "The expression did not produce a result.",
    ) -> None:
        super().__init__(message)


class UnprocessableTokenError(EvaluationError):
    """Raised when an RPN token is neither a valid operand nor a known operator.

    During stack evaluation, every token must be a numeric operand, a constant,
    a supported binary operator, a unary function, or the n-th root operator.
    Any token that matches none of these cannot be processed and this error is
    raised, naming the offending token. With a well-formed parser this is a
    defensive internal invariant, but it is still raised, mapped to a 4xx
    ``ErrorResponse``, and tested.

    Requirement 38.4.
    """

    kind = "unprocessable_token"

    def __init__(
        self,
        message: str | None = None,
        *,
        token: str | None = None,
    ) -> None:
        self.token = token
        if message is None:
            if token is not None:
                message = f"The expression contains an unprocessable token '{token}'."
            else:
                message = "The expression contains an unprocessable token."
        super().__init__(message)


__all__ = [
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
