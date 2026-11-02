"""Shunting Yard linearization: parsed AST -> Reverse Polish (postfix) sequence.

This module is the Stage 4 bridge between the recursive-descent parser and the
stack-based Stack_Evaluator. It performs the "Shunting Yard conversion" of the
Evaluation_Engine migration as a **pure, deterministic post-order traversal** of
the already-correct AST (design "Stage 4 Design (RPN Engine Migration)" ->
"Shunting Yard: two approaches considered", Approach A). It is the fourth member
of the pure computation core (tokenizer -> parser -> rpn -> rpn_evaluator) and
is HTTP-agnostic.

Why linearize the AST rather than run a token-stream Shunting Yard? The parser
already encodes PEMDAS precedence, left-associative ``+ - * /``, right-associative
``^``, the unary-minus-binds-looser-than-``^`` rule (``-3^2 == -9``), functions,
constants, and ``root(x, n)`` directly in the shape of the tree (proved by
Property 1). A post-order walk of that tree *is* a correct postfix sequence:
operands are emitted before their operator, so grouping becomes implicit in the
ordering and **no parenthesis tokens are ever emitted** (Requirement 35.5).
Precedence and associativity (Requirements 35.2-35.4) are inherited from the AST
the walk reads, not re-implemented here.

Linearization rules (design pseudocode)::

    to_rpn(NumberNode n)         -> [Operand(n.value)]
    to_rpn(ConstantNode c)       -> [Constant(c.name)]
    to_rpn(UnaryOpNode("-", x))  -> to_rpn(x) ++ [UnaryFunc("neg")]
    to_rpn(BinaryOpNode(op,l,r)) -> to_rpn(l) ++ to_rpn(r) ++ [BinaryOp(op)]
    to_rpn(FunctionNode(f, x))   -> to_rpn(x) ++ [UnaryFunc(f)]
    to_rpn(RootNode(rad, deg))   -> to_rpn(rad) ++ to_rpn(deg) ++ [RootOp]

Key invariants:

* **Parenthesis-free** (Requirement 35.5): grouping is implicit in postfix order.
* **Postfix placement** (Requirement 35.6): function/constant tokens follow their
  operands in the sequence.
* **Deterministic** (Requirement 35.7): :func:`to_rpn` is a pure function of the
  AST, so the same expression always linearizes to an identical sequence.
* **No partial output on malformed input** (Requirement 35.8): :func:`app.engine.parser.parse`
  raises :class:`EmptyExpressionError`/:class:`InvalidSyntaxError`/
  :class:`UnbalancedParenthesesError`/:class:`InvalidCharacterError` *before*
  ``to_rpn`` ever runs, so a grammar violation never produces a partial
  RPN_Token_Sequence. ``to_rpn`` runs only on a fully valid AST.

The ``Decimal`` operand values are carried through from the AST unchanged; no
value is ever converted to ``float`` (steering: never use raw ``float`` in a
calculation path).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Union

from .errors import UnprocessableTokenError
from .parser import (
    BinaryOpNode,
    ConstantNode,
    FunctionNode,
    Node,
    NumberNode,
    RootNode,
    UnaryOpNode,
)


# --------------------------------------------------------------------------- #
# RPN token model
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Operand:
    """A numeric operand pushed onto the Evaluation_Stack verbatim.

    Attributes:
        value: The exact operand value as a :class:`~decimal.Decimal`, carried
            through from the AST's :class:`~app.engine.parser.NumberNode` without
            conversion to ``float`` so decimal precision is preserved
            (Requirement 36.6).
    """

    value: Decimal


@dataclass(frozen=True)
class Constant:
    """A named mathematical constant resolved by the Stack_Evaluator.

    Attributes:
        name: The constant identifier; either ``"pi"`` or ``"e"``. Its exact
            high-precision :class:`~decimal.Decimal` value is substituted from
            :mod:`app.engine.constants` when the sequence is evaluated, never
            here (Requirements 36.1, 37.4).
    """

    name: str


@dataclass(frozen=True)
class BinaryOp:
    """A binary operator consuming the top two stack operands.

    Attributes:
        symbol: One of ``"+"``, ``"-"``, ``"*"``, ``"/"``, ``"^"``. The
            Stack_Evaluator pops the right operand first and the left operand
            second, preserving non-commutative order (Requirement 36.2).
    """

    symbol: str


@dataclass(frozen=True)
class UnaryFunc:
    """A unary function consuming the single top stack operand.

    Attributes:
        name: The operation identifier: one of the trigonometric / inverse
            trigonometric functions (``"sin"``, ``"cos"``, ``"tan"``, ``"asin"``,
            ``"acos"``, ``"atan"``), ``"ln"``, ``"log10"``, ``"sqrt"``, or the
            unary-minus negation ``"neg"`` (emitted for a
            :class:`~app.engine.parser.UnaryOpNode`). The Stack_Evaluator applies
            the matching unchanged :mod:`app.engine.scientific` kernel
            (Requirements 36.3, 37.1, 37.2).
    """

    name: str


@dataclass(frozen=True)
class RootOp:
    """The n-th root operator consuming the top two stack operands.

    Carries no payload; the Stack_Evaluator pops the degree first and the
    radicand second and applies the same computation as the AST's
    :class:`~app.engine.parser.RootNode` path (Requirement 37.3).
    """


RpnToken = Union[Operand, Constant, BinaryOp, UnaryFunc, RootOp]

#: A parenthesis-free Reverse Polish (postfix) token sequence (Requirement 35.5).
RpnTokenSequence = list[RpnToken]


# --------------------------------------------------------------------------- #
# Linearization: to_rpn()
# --------------------------------------------------------------------------- #
def to_rpn(ast: Node) -> RpnTokenSequence:
    """Linearize a parsed AST into a parenthesis-free postfix token sequence.

    A deterministic post-order traversal (Requirement 35.7) that emits each
    node's operands before the node's own operator token, so the result is a
    valid Reverse Polish sequence with **no parenthesis tokens** (Requirement
    35.5) and with function/constant tokens in postfix position (Requirement
    35.6). Precedence and associativity (Requirements 35.2-35.4) are inherited
    from the structure of ``ast`` and are not re-derived here.

    ``to_rpn`` is only ever called on a fully valid AST: :func:`app.engine.parser.parse`
    raises on any grammar violation before this function runs, so no partial
    sequence is produced for a malformed expression (Requirement 35.8).

    Args:
        ast: The root :class:`~app.engine.parser.Node` of a parsed, valid AST.

    Returns:
        The linearized :data:`RpnTokenSequence`.

    Raises:
        UnprocessableTokenError: Defensively, if ``ast`` contains a node that is
            not one of the known AST node types. A well-formed parser never
            produces such a node, so this is an internal-invariant guard.
    """
    if isinstance(ast, NumberNode):
        return [Operand(ast.value)]

    if isinstance(ast, ConstantNode):
        return [Constant(ast.name)]

    if isinstance(ast, UnaryOpNode):
        # Only unary "-" exists in the grammar; it becomes the "neg" kernel.
        return [*to_rpn(ast.operand), UnaryFunc("neg")]

    if isinstance(ast, BinaryOpNode):
        return [*to_rpn(ast.left), *to_rpn(ast.right), BinaryOp(ast.op)]

    if isinstance(ast, FunctionNode):
        return [*to_rpn(ast.operand), UnaryFunc(ast.name)]

    if isinstance(ast, RootNode):
        return [*to_rpn(ast.radicand), *to_rpn(ast.degree), RootOp()]

    # Unknown node type. With a well-formed parser this is unreachable, but we
    # raise defensively rather than silently dropping the node (Requirement
    # 35.8 keeps malformed input out of this path to begin with).
    raise UnprocessableTokenError(token=repr(ast))


__all__ = [
    "Operand",
    "Constant",
    "BinaryOp",
    "UnaryFunc",
    "RootOp",
    "RpnToken",
    "RpnTokenSequence",
    "to_rpn",
]
