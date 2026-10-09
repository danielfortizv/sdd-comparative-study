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
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    """Request body for the Evaluate_Endpoint.

    The ``expression`` string is constrained to 1-256 characters. Pydantic
    rejects a missing field, a non-string value, or a string outside this
    length range, which the API layer surfaces as a 4xx ``ErrorResponse``.

    Requirements 1.5, 5.2, 5.6.
    """

    expression: str = Field(min_length=1, max_length=256)


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
