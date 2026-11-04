"""Tokenizer for the Evaluation_Engine.

Converts a raw expression string into a stream of :class:`Token` objects. The
tokenizer is the first stage of the pure computation core (tokenizer -> parser
-> evaluator) and is HTTP-agnostic.

Recognized lexemes (design "Token Model" and "Components and Interfaces"):

* numbers with at most a single decimal point (e.g. ``12``, ``3.14``, ``.5``)
* the binary operators ``+ - * / ^``
* parentheses ``(`` and ``)``
* function identifiers ``sin cos tan asin acos atan ln log10 sqrt root``
  (Stage 2, Requirements 17.1, 17.2, 18.4, 18.5)
* constant identifiers ``pi`` and ``e`` (Stage 2, Requirement 19.1, 19.2)
* the argument separator ``,`` used by the two-argument n-th root
* an ``EOF`` sentinel appended at the end of the stream

Insignificant whitespace is skipped. Any character outside the allowed set
raises :class:`InvalidCharacterError` with a descriptive, position-aware
message (Requirement 4.4). An identifier run that matches no known function or
constant name raises :class:`InvalidFunctionError` naming the unknown
identifier and its position (Requirement 24.8). Every token preserves its
source ``position`` so the parser and error messages can point at the offending
location (Requirement 6.1).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from .errors import InvalidCharacterError, InvalidFunctionError


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
    # Stage 2 additions (design "Tokenizer — new lexemes").
    FUNCTION = auto()
    CONSTANT = auto()
    COMMA = auto()
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


#: Single-character operators, parentheses, and the argument separator mapped
#: to their token type.
_SINGLE_CHAR_TOKENS: dict[str, TokenType] = {
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "^": TokenType.CARET,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    ",": TokenType.COMMA,
}

#: Known function identifiers (design "new lexemes"). An identifier run equal to
#: one of these becomes a :attr:`TokenType.FUNCTION` token. ``log10`` is handled
#: specially during scanning (see :func:`tokenize`) because its name ends in
#: digits, which are not part of a letters-only identifier run.
_FUNCTION_NAMES: frozenset[str] = frozenset(
    {
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "ln",
        "log10",
        "sqrt",
        "root",
    }
)

#: Known constant identifiers (Requirements 19.1, 19.2). An identifier run equal
#: to one of these becomes a :attr:`TokenType.CONSTANT` token.
_CONSTANT_NAMES: frozenset[str] = frozenset({"pi", "e"})


def tokenize(expression: str) -> list[Token]:
    """Convert ``expression`` into a list of tokens terminated by an ``EOF`` token.

    Numbers are read greedily and may contain at most one decimal point; a second
    decimal point inside the same number begins a new (invalid) run that will be
    rejected downstream by the parser, but the point itself is a legal character
    so it is not rejected here. Whitespace is skipped.

    On an ASCII letter the scanner reads a maximal ``[a-zA-Z]`` run (digits are
    not part of an identifier, so ``sin2`` lexes as ``sin`` then ``2``). As a
    single special case, a ``log`` run immediately followed by ``10`` consumes
    those two digits so ``log10`` is recognized as one keyword. The run is then
    matched against the known-name tables: a function name becomes a
    :attr:`TokenType.FUNCTION` token, a constant name becomes a
    :attr:`TokenType.CONSTANT` token, and anything else (including a bare
    ``log``) raises :class:`InvalidFunctionError`. A ``,`` becomes a
    :attr:`TokenType.COMMA` token. Any character that is not a digit, a decimal
    point, an allowed operator, a parenthesis, an ASCII letter, or a comma raises
    :class:`InvalidCharacterError`.

    Args:
        expression: The raw expression string to tokenize.

    Returns:
        A list of :class:`Token` objects ending with a single ``EOF`` token whose
        ``position`` is the length of the source string.

    Raises:
        InvalidCharacterError: If ``expression`` contains a disallowed character.
        InvalidFunctionError: If ``expression`` contains a letter-run that matches
            no known function or constant name.
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

        # Identifiers: a maximal run of ASCII letters matched against the known
        # function/constant tables. Digits are not part of an identifier, so a
        # run stops at the first non-letter (e.g. ``sin2`` -> ``sin`` then ``2``).
        if char.isascii() and char.isalpha():
            start = index
            while index < length and expression[index].isascii() and (
                expression[index].isalpha()
            ):
                index += 1
            name = expression[start:index]

            # Special case: ``log10`` is a dedicated keyword whose name ends in
            # digits. After the ``log`` letter-run, if the next two characters
            # are ``10``, consume them as part of the ``log10`` keyword.
            if name == "log" and expression[index : index + 2] == "10":
                index += 2
                name = "log10"

            if name in _FUNCTION_NAMES:
                tokens.append(Token(TokenType.FUNCTION, name, start))
                continue
            if name in _CONSTANT_NAMES:
                tokens.append(Token(TokenType.CONSTANT, name, start))
                continue

            # An unrecognized identifier run (including a bare ``log``) is an
            # unknown function or name (Requirement 24.8).
            raise InvalidFunctionError(name=name, position=start)

        # Single-character operators, parentheses, and the argument separator.
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
