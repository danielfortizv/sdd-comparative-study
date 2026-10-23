"""Unit tests for the Evaluation_Engine tokenizer (task 2.3).

Covers recognition of numbers, every operator, parentheses, and whitespace
skipping, plus the rejection of disallowed characters via
:class:`InvalidCharacterError`.

_Requirements: 4.4_
"""

from __future__ import annotations

import pytest

from app.engine.errors import InvalidCharacterError
from app.engine.tokenizer import Token, TokenType, tokenize


def _types(expression: str) -> list[TokenType]:
    """Tokenize and return the token-type sequence (EOF included)."""
    return [token.type for token in tokenize(expression)]


# --------------------------------------------------------------------------- #
# Numbers
# --------------------------------------------------------------------------- #
def test_single_integer_number() -> None:
    tokens = tokenize("42")
    assert tokens == [
        Token(TokenType.NUMBER, "42", 0),
        Token(TokenType.EOF, "", 2),
    ]


def test_decimal_number_recognized() -> None:
    tokens = tokenize("3.14")
    assert tokens[0] == Token(TokenType.NUMBER, "3.14", 0)
    assert tokens[-1].type is TokenType.EOF


def test_leading_dot_number_recognized() -> None:
    tokens = tokenize(".5")
    assert tokens[0] == Token(TokenType.NUMBER, ".5", 0)


def test_second_decimal_point_terminates_number_run() -> None:
    # A second dot starts a new run; the tokenizer does not swallow it silently.
    tokens = tokenize("1.2.3")
    numbers = [t for t in tokens if t.type is TokenType.NUMBER]
    assert numbers[0] == Token(TokenType.NUMBER, "1.2", 0)
    # The remaining ".3" is lexed as a separate NUMBER run.
    assert Token(TokenType.NUMBER, ".3", 3) in tokens


# --------------------------------------------------------------------------- #
# Operators
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    ("lexeme", "expected_type"),
    [
        ("+", TokenType.PLUS),
        ("-", TokenType.MINUS),
        ("*", TokenType.STAR),
        ("/", TokenType.SLASH),
        ("^", TokenType.CARET),
    ],
)
def test_each_operator_recognized(lexeme: str, expected_type: TokenType) -> None:
    tokens = tokenize(lexeme)
    assert tokens[0] == Token(expected_type, lexeme, 0)
    assert tokens[-1].type is TokenType.EOF


def test_all_operators_in_sequence() -> None:
    assert _types("1+2-3*4/5^6") == [
        TokenType.NUMBER,
        TokenType.PLUS,
        TokenType.NUMBER,
        TokenType.MINUS,
        TokenType.NUMBER,
        TokenType.STAR,
        TokenType.NUMBER,
        TokenType.SLASH,
        TokenType.NUMBER,
        TokenType.CARET,
        TokenType.NUMBER,
        TokenType.EOF,
    ]


# --------------------------------------------------------------------------- #
# Parentheses
# --------------------------------------------------------------------------- #
def test_parentheses_recognized() -> None:
    tokens = tokenize("(1)")
    assert tokens == [
        Token(TokenType.LPAREN, "(", 0),
        Token(TokenType.NUMBER, "1", 1),
        Token(TokenType.RPAREN, ")", 2),
        Token(TokenType.EOF, "", 3),
    ]


# --------------------------------------------------------------------------- #
# Whitespace skipping
# --------------------------------------------------------------------------- #
def test_whitespace_is_skipped() -> None:
    tokens = tokenize("  1 +   2 ")
    assert tokens == [
        Token(TokenType.NUMBER, "1", 2),
        Token(TokenType.PLUS, "+", 4),
        Token(TokenType.NUMBER, "2", 8),
        Token(TokenType.EOF, "", 10),
    ]


def test_mixed_whitespace_kinds_skipped() -> None:
    assert _types("1\t+\n2") == [
        TokenType.NUMBER,
        TokenType.PLUS,
        TokenType.NUMBER,
        TokenType.EOF,
    ]


def test_whitespace_only_yields_only_eof() -> None:
    tokens = tokenize("   ")
    assert tokens == [Token(TokenType.EOF, "", 3)]


def test_empty_string_yields_only_eof() -> None:
    tokens = tokenize("")
    assert tokens == [Token(TokenType.EOF, "", 0)]


# --------------------------------------------------------------------------- #
# EOF sentinel position
# --------------------------------------------------------------------------- #
def test_eof_position_equals_source_length() -> None:
    expression = "12+34"
    tokens = tokenize(expression)
    assert tokens[-1] == Token(TokenType.EOF, "", len(expression))


# --------------------------------------------------------------------------- #
# Invalid characters (Requirement 4.4)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("bad", ["&", "#", "%", "@", "!", "?", "$", "~", "["])
def test_disallowed_character_raises(bad: str) -> None:
    with pytest.raises(InvalidCharacterError):
        tokenize(f"2 {bad} 3")


def test_invalid_character_reports_character_and_position() -> None:
    with pytest.raises(InvalidCharacterError) as exc_info:
        tokenize("2 & 3")
    error = exc_info.value
    assert error.character == "&"
    assert error.position == 2
    assert error.kind == "invalid_character"
    # The default message is position/character aware.
    assert "&" in error.message
