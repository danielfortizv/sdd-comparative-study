"""Recursive-descent parser for the Evaluation_Engine.

Consumes the token stream produced by :mod:`app.engine.tokenizer` and builds an
explicit abstract syntax tree (AST) that encodes PEMDAS precedence and
associativity directly in the shape of its productions. It is the second stage
of the pure computation core (tokenizer -> parser -> evaluator) and is
HTTP-agnostic.

Grammar (design "Data Models" -> "Grammar"), ordered lowest -> highest
precedence::

    expression = term , { ("+" | "-") , term } ;       (* add/sub, left-assoc  *)
    term       = factor , { ("*" | "/") , factor } ;    (* mul/div, left-assoc  *)
    factor     = ("-" , factor) | power ;               (* unary minus          *)
    power      = primary , [ "^" , factor ] ;           (* exponent, right-assoc*)
    primary    = number | "(" , expression , ")" ;

Precedence, low -> high: ``+ -`` < ``* /`` < unary ``-`` < ``^`` < parentheses.
Because ``power = primary , [ "^" , factor ]`` recurses on the right through
``factor``, ``^`` is right-associative and its right operand may itself carry a
unary minus (``2^2^3 == 256`` and ``2^-3`` both parse; Requirement 2.4). Because
the exponent's *base* is a bare ``primary`` while unary minus sits *above* the
``^`` chain (``factor`` wraps ``power``), ``-3^2`` parses as ``-(3^2) == -9``,
applying the exponent before the unary minus (Requirement 2.6). This matches the
standard mathematical convention (and Python's ``-3 ** 2 == -9``).

.. note::
   The design's prose precedence table lists ``^ < unary -``, but its own stated
   goal (``-3^2 == -9``) and Requirement 2.6 require the exponent to bind tighter
   than unary minus. This implementation follows the authoritative requirement
   (exponentiation before unary minus), which is why ``factor`` wraps ``power``.

The parser fails fast on the first violation, preserving source positions for
descriptive messages:

* :class:`EmptyExpressionError` on empty / whitespace-only input (Requirement 4.5)
* :class:`InvalidSyntaxError` on invalid operator sequences (Requirement 4.2)
* :class:`UnbalancedParenthesesError` on unclosed / unmatched parentheses (Req 4.3)

:func:`render` is the inverse of :func:`parse`: it serializes an AST back to an
expression string that re-parses to a structurally equivalent tree, adding
explicit parentheses where needed to preserve precedence and associativity
(Requirement 6.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Union

from .errors import (
    EmptyExpressionError,
    InvalidSyntaxError,
    UnbalancedParenthesesError,
)
from .tokenizer import Token, TokenType, tokenize


# --------------------------------------------------------------------------- #
# AST node types
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class NumberNode:
    """A numeric literal.

    Attributes:
        value: The exact operand value as a :class:`~decimal.Decimal`,
            constructed directly from the source lexeme (never via ``float``)
            so decimal precision is preserved (Requirement 3.3).
    """

    value: Decimal


@dataclass(frozen=True)
class UnaryOpNode:
    """A unary operation applied to a single operand.

    Attributes:
        op: The unary operator; only ``"-"`` is supported.
        operand: The operand node.
    """

    op: str
    operand: "Node"


@dataclass(frozen=True)
class BinaryOpNode:
    """A binary operation over two operands.

    Attributes:
        op: One of ``"+"``, ``"-"``, ``"*"``, ``"/"``, ``"^"``.
        left: The left operand node.
        right: The right operand node.
    """

    op: str
    left: "Node"
    right: "Node"


Node = Union[NumberNode, UnaryOpNode, BinaryOpNode]


# --------------------------------------------------------------------------- #
# Parser
# --------------------------------------------------------------------------- #
_ADD_SUB = {TokenType.PLUS: "+", TokenType.MINUS: "-"}
_MUL_DIV = {TokenType.STAR: "*", TokenType.SLASH: "/"}


class _Parser:
    """Internal recursive-descent parser over a token list.

    A fresh instance is created per :func:`parse` call. The public module-level
    :func:`parse` function is the supported entry point.
    """

    def __init__(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._pos = 0

    # -- token helpers ----------------------------------------------------- #
    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        token = self._tokens[self._pos]
        if token.type is not TokenType.EOF:
            self._pos += 1
        return token

    # -- grammar productions ---------------------------------------------- #
    def parse(self) -> Node:
        """Parse a complete expression and assert the stream is fully consumed."""
        node = self._expression()
        current = self._peek()
        if current.type is not TokenType.EOF:
            # Trailing tokens that were not consumed by the grammar. A stray
            # closing parenthesis is an unbalanced-parentheses violation; any
            # other leftover token is an invalid operator sequence.
            if current.type is TokenType.RPAREN:
                raise UnbalancedParenthesesError(
                    message=(
                        f"Unmatched closing parenthesis at position "
                        f"{current.position}."
                    ),
                    position=current.position,
                )
            raise InvalidSyntaxError(position=current.position)
        return node

    def _expression(self) -> Node:
        """expression = term , { ("+" | "-") , term } ;  (left-associative)"""
        node = self._term()
        while self._peek().type in _ADD_SUB:
            op_token = self._advance()
            right = self._term()
            node = BinaryOpNode(_ADD_SUB[op_token.type], node, right)
        return node

    def _term(self) -> Node:
        """term = factor , { ("*" | "/") , factor } ;  (left-associative)"""
        node = self._factor()
        while self._peek().type in _MUL_DIV:
            op_token = self._advance()
            right = self._factor()
            node = BinaryOpNode(_MUL_DIV[op_token.type], node, right)
        return node

    def _factor(self) -> Node:
        """factor = ("-" , factor) | power ;  (unary minus, looser than ^)"""
        if self._peek().type is TokenType.MINUS:
            self._advance()
            operand = self._factor()
            return UnaryOpNode("-", operand)
        return self._power()

    def _power(self) -> Node:
        """power = primary , [ "^" , factor ] ;  (exponent, right-associative)

        The base is a bare ``primary`` (so ``-3^2`` groups as ``-(3^2)``), while
        the exponent recurses back into ``factor`` so it is right-associative and
        may itself be a unary-minus expression (``2^-3``): ``2^2^3 == 2^(2^3)``.
        """
        node = self._primary()
        if self._peek().type is TokenType.CARET:
            self._advance()
            right = self._factor()
            node = BinaryOpNode("^", node, right)
        return node

    def _primary(self) -> Node:
        """primary = number | "(" , expression , ")" ;"""
        token = self._peek()

        if token.type is TokenType.NUMBER:
            self._advance()
            return NumberNode(_decimal_from_lexeme(token))

        if token.type is TokenType.LPAREN:
            open_token = self._advance()
            inner = self._expression()
            closing = self._peek()
            if closing.type is not TokenType.RPAREN:
                raise UnbalancedParenthesesError(position=open_token.position)
            self._advance()
            return inner

        # No valid primary here. Distinguish "nothing at all" (empty input) from
        # a misplaced operator / premature end.
        if token.type is TokenType.EOF:
            if self._pos == 0:
                raise EmptyExpressionError()
            raise InvalidSyntaxError(position=token.position)
        raise InvalidSyntaxError(position=token.position)


def _decimal_from_lexeme(token: Token) -> Decimal:
    """Build an exact :class:`~decimal.Decimal` from a NUMBER token's lexeme.

    A malformed numeric lexeme (e.g. a bare ``.`` or a run containing a second
    decimal point that slipped through the tokenizer) is an invalid syntax
    violation, reported with the token's source position (Requirement 4.2).
    """
    try:
        return Decimal(token.lexeme)
    except InvalidOperation as exc:  # pragma: no cover - defensive
        raise InvalidSyntaxError(
            message=(
                f"Invalid number '{token.lexeme}' at position {token.position}."
            ),
            position=token.position,
        ) from exc


def parse(expression: str) -> Node:
    """Parse ``expression`` into an AST conforming to PEMDAS precedence.

    Args:
        expression: The raw expression string.

    Returns:
        The root :class:`Node` of the parsed AST.

    Raises:
        EmptyExpressionError: If ``expression`` is empty or only whitespace.
        InvalidCharacterError: If ``expression`` contains a disallowed character
            (propagated from the tokenizer).
        InvalidSyntaxError: On an invalid operator sequence or malformed number.
        UnbalancedParenthesesError: On an unclosed or unmatched parenthesis.
    """
    if expression is None or expression.strip() == "":
        raise EmptyExpressionError()
    tokens = tokenize(expression)
    return _Parser(tokens).parse()


# --------------------------------------------------------------------------- #
# render(): inverse of parse() used by the round-trip property (Req 6.3)
# --------------------------------------------------------------------------- #
#: Binary operator precedence, higher binds tighter. Mirrors the grammar.
_BINARY_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}


def render(node: "Node") -> str:
    """Serialize an AST back into an expression string.

    The produced string re-parses (:func:`parse`) into a tree that is
    structurally equivalent to ``node`` and evaluates to the same value.
    Explicit parentheses are inserted wherever operator precedence or
    associativity would otherwise be lost, so the round-trip preserves PEMDAS
    structure (Requirement 6.3).

    Args:
        node: The AST node to render.

    Returns:
        An expression string that parses back to an equivalent structure.

    Raises:
        TypeError: If ``node`` is not a recognized AST node type.
    """
    if isinstance(node, NumberNode):
        return _render_number(node.value)

    if isinstance(node, UnaryOpNode):
        operand = node.operand
        rendered = render(operand)
        # Unary minus binds looser than ^ but tighter than * / + -. Its operand
        # is a `factor` in the grammar, so a bare number, a nested unary, or an
        # exponentiation may follow it directly (`-3`, `--5`, `-3^2` == -(3^2)).
        # A + - * / operand must be parenthesized, otherwise the surrounding
        # binary operator would capture the wrong subtree (`-(1+2)`, `-(2*3)`).
        if isinstance(operand, BinaryOpNode) and operand.op != "^":
            rendered = f"({rendered})"
        return f"-{rendered}"

    if isinstance(node, BinaryOpNode):
        op = node.op
        left = _render_operand(node.left, parent_op=op, is_right=False)
        right = _render_operand(node.right, parent_op=op, is_right=True)
        return f"{left} {op} {right}"

    raise TypeError(f"Cannot render unknown AST node: {node!r}")


def _render_operand(child: "Node", *, parent_op: str, is_right: bool) -> str:
    """Render an operand of a binary op, parenthesizing to preserve structure.

    Precedence, low -> high, matches the grammar: ``+ -`` < ``* /`` < unary ``-``
    < ``^`` < primary. Parentheses are added whenever the child would otherwise
    be re-parsed under a different grouping than the AST specifies.
    """
    rendered = render(child)
    parent_prec = _BINARY_PRECEDENCE[parent_op]

    if isinstance(child, NumberNode):
        # Non-negative literal (unary minus is its own node); never needs wrapping.
        return rendered

    if isinstance(child, UnaryOpNode):
        # Unary minus binds looser than ^ but tighter than * / + -.
        if parent_op == "^":
            # As the base of ^ the grammar demands a bare primary, and even as
            # the exponent a leading unary is fine (`2^-3`) but a base unary must
            # be wrapped (`(-3)^2`). Wrap the base; leave a unary exponent bare.
            return f"({rendered})" if not is_right else rendered
        # For * / + - a unary operand groups tighter and needs no parentheses.
        return rendered

    # child is a BinaryOpNode.
    child_prec = _BINARY_PRECEDENCE[child.op]
    needs_parens = False
    if child_prec < parent_prec:
        needs_parens = True
    elif child_prec == parent_prec:
        # Equal precedence: associativity of the parent decides. Left-assoc
        # (+ - * /) keeps the left child bare and wraps the right; right-assoc
        # (^) keeps the right child bare and wraps the left.
        if parent_op == "^":
            needs_parens = not is_right
        else:
            needs_parens = is_right

    return f"({rendered})" if needs_parens else rendered


def _render_number(value: Decimal) -> str:
    """Render a Decimal operand as a lexeme the tokenizer accepts.

    Uses a plain (non-scientific) decimal string so it round-trips through the
    tokenizer, which recognizes only digits and a single decimal point. A
    negative value is emitted as a parenthesized unary-minus form so it parses
    back into an equivalent structure rather than being swallowed as a binary
    operator context.
    """
    if value < 0:
        return f"(-{_render_number(-value)})"
    text = format(value, "f")
    return text


__all__ = [
    "NumberNode",
    "UnaryOpNode",
    "BinaryOpNode",
    "Node",
    "parse",
    "render",
]
