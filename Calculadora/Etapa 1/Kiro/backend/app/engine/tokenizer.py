"""Tokenizer for the Evaluation_Engine.

Converts a raw expression string into a stream of :class:`Token` objects. The
tokenizer is the first stage of the pure computation core (tokenizer -> parser
-> evaluator) and is HTTP-agnostic.

Recognized lexemes (design "Token Model" and "Components and Interfaces"):

* numbers with at most a single decimal point (e.g. ``12``, ``3.14``, ``.5``)
* the binary operators ``+ - * / ^``
* parentheses ``(`` and ``)``
* an ``EOF`` sentinel appended at the end of the stream

Insignificant whitespace is skipped. Any character outside the allowed set
raises :class:`InvalidCharacterError` with a descriptive, position-aware
message (Requirement 4.4). Every token preserves its source ``position`` so the
parser and error messages can point at the offending location (Requirement 6.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .errors import InvalidCharacterError


class TokenType(Enum):
    """The kinds of tokens produced by the :class:`Tokenizer`."""

    NUMBER = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    CARET = auto()
    LPAREN = auto()
    RPAREN = auto()
    EOF = auto()


@dataclass(frozen=True)
class Token:
    """A single lexical token.

    Attributes:
        type: The :class:`TokenType` category of the token.
        lexeme: The exact source text of the token (empty for ``EOF``).
        position: The 0-based index in the source string where the token begins.
            Used to build descriptive, position-aware error messages.
    """

    type: TokenType
    lexeme: str
    position: int


#: Single-character operators and parentheses mapped to their token type.
_SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "^": TokenType.CARET,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
}


def tokenize(expression: str) -> list[Token]:
    """Convert ``expression`` into a list of tokens terminated by an ``EOF`` token.

    Numbers are read greedily and may contain at most one decimal point; a second
    decimal point inside the same number begins a new (invalid) run that will be
    rejected downstream by the parser, but the point itself is a legal character
    so it is not rejected here. Whitespace is skipped. Any character that is not a
    digit, a decimal point, an allowed operator, or a parenthesis raises
    :class:`InvalidCharacterError`.

    Args:
        expression: The raw expression string to tokenize.

    Returns:
        A list of :class:`Token` objects ending with a single ``EOF`` token whose
        ``position`` is the length of the source string.

    Raises:
        InvalidCharacterError: If ``expression`` contains a disallowed character.
    """
    tokens: list[Token] = []
    index = 0
    length = len(expression)

    while index < length:
        char = expression[index]

        # Skip insignificant whitespace.
        if char.isspace():
            index += 1
            continue

        # Numbers: a run of digits with at most one decimal point.
        if char.isdigit() or char == ".":
            start = index
            seen_dot = False
            while index < length and (
                expression[index].isdigit() or expression[index] == "."
            ):
                if expression[index] == ".":
                    # A second dot terminates this number; the parser will reject
                    # the resulting malformed operand. Stop the run so the extra
                    # dot is not swallowed silently.
                    if seen_dot:
                        break
                    seen_dot = True
                index += 1
            lexeme = expression[start:index]
            tokens.append(Token(TokenType.NUMBER, lexeme, start))
            continue

        # Single-character operators and parentheses.
        token_type = _SINGLE_CHAR_TOKENS.get(char)
        if token_type is not None:
            tokens.append(Token(token_type, char, index))
            index += 1
            continue

        # Anything else is an invalid character (Requirement 4.4).
        raise InvalidCharacterError(character=char, position=index)

    tokens.append(Token(TokenType.EOF, "", length))
    return tokens


__all__ = ["TokenType", "Token", "tokenize"]
