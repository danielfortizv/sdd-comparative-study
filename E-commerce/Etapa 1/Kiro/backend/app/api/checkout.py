"""Checkout API router (``POST /checkout/confirm``).

Exposes the non-persistent simulated-purchase confirmation over HTTP/JSON
(Requirements 10.1, 10.2). The router is a thin request/response layer: it
delegates summary building and validation to the checkout service and maps a
``CheckoutError`` to a structured JSON error with an appropriate status code,
without exposing internal detail (Error Handling section of the design).

The response contains only the purchased-items summary and total; it carries
no order ID and no creation timestamp, and no order record is stored
(R10.1, R10.2). The empty-cart guard (R9.5) is re-checked server-side.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.checkout import CheckoutConfirmation, CheckoutRequest
from app.services.checkout_service import CheckoutError, confirm_checkout

router = APIRouter(tags=["checkout"])


@router.post("/checkout/confirm", response_model=CheckoutConfirmation)
def confirm_checkout_endpoint(request: CheckoutRequest) -> CheckoutConfirmation:
    """Build and return a non-persistent confirmation for a Simulated_Purchase.

    Accepts the submitted cart contents (product identifiers and quantities),
    resolves product details from catalog data, and returns the purchased-items
    summary and total. Rejects an empty submission (server-side empty-cart
    guard, R9.5) and other inconsistent submissions with a structured error.
    """
    try:
        return confirm_checkout(request)
    except CheckoutError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": error.code, "message": error.message},
        ) from error
