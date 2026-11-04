"""Pydantic request/response models for the Evaluate_Endpoint.

These models define the typed JSON contract of ``POST /api/v1/evaluate`` (see
design "API Contract" and "Request/Response Models"). They are Pydantic v2
(``pydantic>=2.6``) models.

Success and error payloads are mutually exclusive: a success response carries a
``result`` field and omits ``error``; an ``ErrorResponse`` carries an ``error``
field and omits ``result``. This makes the response an unambiguous
success-XOR-error discriminated union (Requirement 5.5).

The ``result`` field is a **string** so the exact decimal representation is
preserved across JSON serialization, avoiding any float coercion that would
reintroduce precision loss (Requirements 3.1-3.3, 5.3).

The Stage 2 scientific extension adds an optional ``angle_mode`` to the request
that selects the unit (radians or degrees) used to interpret trigonometric
arguments. It defaults to radians when omitted and is validated against a fixed
literal set so any other value is rejected as a 4xx ``ErrorResponse``
(Requirements 24.2, 24.3, 24.4, 17.9, 17.10).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    """Request body for the Evaluate_Endpoint.

    The ``expression`` string is constrained to 1-256 characters. Pydantic
    rejects a missing field, a non-string value, or a string outside this
    length range, which the API layer surfaces as a 4xx ``ErrorResponse``.

    The optional ``angle_mode`` selects how trigonometric arguments are
    interpreted. It is restricted to the literals ``"radians"`` and
    ``"degrees"`` and defaults to ``"radians"`` when the field is omitted
    (Requirements 24.2, 24.3, 17.9). Any other value fails Pydantic literal
    validation and is surfaced as a 4xx ``ErrorResponse`` (Requirements 24.4,
    17.10). The mode only affects trigonometric and inverse-trigonometric
    functions; all other arithmetic is unaffected by it.

    Requirements 1.5, 5.2, 5.6, 24.2, 24.3, 24.4, 17.9, 17.10.
    """

    expression: str = Field(min_length=1, max_length=256)
    angle_mode: Literal["radians", "degrees"] = "radians"


class EvaluateSuccess(BaseModel):
    """Success response for a successfully evaluated expression.

    Carries the calculated result as a string to preserve exact decimal
    precision. Requirements 5.3, 5.5.
    """

    result: str


class ErrorResponse(BaseModel):
    """Structured error payload for any failed evaluation.

    Carries a descriptive, human-readable ``error`` message and never a
    ``result`` field. Requirements 5.4, 5.5.
    """

    error: str


__all__ = [
    "EvaluateRequest",
    "EvaluateSuccess",
    "ErrorResponse",
]
