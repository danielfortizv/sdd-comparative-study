"""High-precision mathematical constants for the Evaluation_Engine.

This module stores the mathematical constants ``pi`` and ``e`` as exact
:class:`~decimal.Decimal` values built directly from string literals. It is a
leaf module of the pure computation core (tokenizer -> parser -> evaluator):
it imports nothing from the rest of the engine and is HTTP-agnostic.

Design highlights ("High-precision constants" / "Constants
(engine/constants.py)"):

* ``pi`` and ``e`` are stored as :class:`~decimal.Decimal` literals with at
  least 50 significant digits -- well beyond the >=10 significant digits the
  public contract exposes and matching the evaluator's working precision
  (``prec = 50``). They are returned as exact :class:`~decimal.Decimal`
  operands when a ``ConstantNode`` is evaluated (Requirements 19.1, 19.2).
* Each constant is built via ``Decimal("...")`` from its string literal so the
  value is *exact*; it is never constructed from a binary ``float``, which
  would silently lose precision (consistent with the ``product.md`` rule that
  no raw ``float`` ever appears in a calculation path).
* ``pi`` is the sole basis for degree<->radian conversion (Requirement 17.5):
  ``radians = degrees * pi / 180`` and ``degrees = radians * 180 / pi``. The
  scientific operations module imports :data:`PI` from here so there is a
  single source of truth for the constant.
"""

from __future__ import annotations

from decimal import Decimal

# --------------------------------------------------------------------------- #
# High-precision constant literals
# --------------------------------------------------------------------------- #
#: The ratio of a circle's circumference to its diameter, to 50 significant
#: digits. Built from a string literal so the value is exact (Requirement 19.1).
PI: Decimal = Decimal("3.1415926535897932384626433832795028841971693993751")

#: Euler's number, the base of the natural logarithm, to 50 significant digits.
#: Built from a string literal so the value is exact (Requirement 19.2).
E: Decimal = Decimal("2.7182818284590452353602874713526624977572470936999")

#: Mapping from a constant's source name (as lexed by the tokenizer) to its
#: exact :class:`~decimal.Decimal` value. The tokenizer/parser validate names
#: before a ``ConstantNode`` is ever created, so the evaluator can look a name
#: up here directly.
CONSTANTS: dict[str, Decimal] = {"pi": PI, "e": E}


def constant_value(name: str) -> Decimal:
    """Return the exact :class:`~decimal.Decimal` value for a constant ``name``.

    This is the lookup the evaluator uses when it walks a ``ConstantNode``: the
    tokenizer and parser have already validated that ``name`` is one of the
    known constants (``"pi"`` or ``"e"``), so a known name always resolves to an
    exact operand with >=50 significant digits (Requirements 19.1, 19.2).

    Args:
        name: The constant's source name, ``"pi"`` or ``"e"``.

    Returns:
        The exact :class:`~decimal.Decimal` value of the named constant.

    Raises:
        KeyError: If ``name`` is not a recognized constant. This is defensive;
            upstream lexing/parsing guarantees only known names reach here.
    """
    return CONSTANTS[name]


__all__ = ["PI", "E", "CONSTANTS", "constant_value"]
