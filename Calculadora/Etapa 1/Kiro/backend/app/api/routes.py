"""FastAPI router for the Evaluate_Endpoint.

This module defines the transport layer for ``POST /api/v1/evaluate`` (design
"API Layer"). The route is a thin adapter: it accepts a validated
:class:`~app.api.schemas.EvaluateRequest`, delegates all arithmetic to the pure
:func:`app.engine.evaluate_expression` entry point, and maps a successful
outcome to a :class:`~app.api.schemas.EvaluateSuccess` body.

Responsibilities and boundaries
-------------------------------
* Success path (Requirements 5.1, 5.2, 5.3, 5.5): on a valid expression the
  handler returns HTTP ``200`` with ``{"result": "<string>"}`` and
  ``Content-Type: application/json``. The :class:`~decimal.Decimal` produced by
  the engine is converted to a **string** so its exact representation survives
  JSON serialization with no float coercion (design "API Contract").
* The response is an unambiguous success-XOR-error discriminated union: this
  route only ever emits a ``result`` and never an ``error`` (Requirement 5.5).
* Failure path: any :class:`~app.engine.errors.EvaluationError` subclass raised
  by the engine is intentionally allowed to propagate. It is translated into a
  4xx ``ErrorResponse`` by the exception handlers registered in
  :mod:`app.main` (task 4.3), keeping HTTP error mapping out of the route.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import EvaluateRequest, EvaluateSuccess
from app.engine import evaluate_expression

router = APIRouter(prefix="/api/v1", tags=["evaluate"])


@router.post(
    "/evaluate",
    response_model=EvaluateSuccess,
    summary="Evaluate an arithmetic expression",
)
def evaluate(request: EvaluateRequest) -> EvaluateSuccess:
    """Evaluate ``request.expression`` and return the exact decimal result.

    The request body is validated by Pydantic before this handler runs
    (1-256 characters, present, string). The handler delegates the arithmetic
    to :func:`app.engine.evaluate_expression` and serializes the resulting
    :class:`~decimal.Decimal` as a string.

    Args:
        request: The validated request body carrying the expression to
            evaluate.

    Returns:
        An :class:`~app.api.schemas.EvaluateSuccess` whose ``result`` is the
        exact decimal value rendered as a string (Requirements 5.3, 5.5).

    Raises:
        EvaluationError: Any subclass (empty input, invalid character, invalid
            syntax, unbalanced parentheses, division by zero) propagates
            unchanged to be mapped to a 4xx ``ErrorResponse`` by the
            application-level exception handlers.
    """
    result = evaluate_expression(request.expression)
    return EvaluateSuccess(result=str(result))


__all__ = ["router"]
