"""Checkout confirmation service (business logic for the simulated purchase).

This service builds the non-persistent confirmation summary for a
Simulated_Purchase from the submitted cart contents and the shared catalog
data (Requirements 10.1, 10.2). It resolves each submitted product's name and
unit price from catalog data by ``productId`` so product information stays
consistent across the journey (R11), computes ``lineTotal = unitPrice *
quantity`` and ``total = sum(lineTotal)``, and marks the confirmation as
simulated.

Nothing is persisted: no order record is stored and the confirmation carries
no order ID and no creation timestamp (R10.1). The empty-cart guard (R9.5),
enforced on the frontend before the call, is re-checked here by rejecting an
empty submission.
"""

from __future__ import annotations

from app.data import catalog
from app.models.checkout import (
    CheckoutConfirmation,
    CheckoutConfirmationItem,
    CheckoutRequest,
)


class CheckoutError(Exception):
    """Raised when a checkout submission cannot be confirmed.

    Carries a stable machine-readable ``code`` and a human-readable
    ``message`` so the API layer can return a structured JSON error without
    leaking internal detail (Error Handling section of the design).

    Attributes:
        code: Stable error code identifying the failure category.
        message: Human-readable description of the failure.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def confirm_checkout(request: CheckoutRequest) -> CheckoutConfirmation:
    """Build the non-persistent confirmation summary for a Simulated_Purchase.

    Resolves each submitted item's product details (name, unit price) from the
    shared catalog data by ``productId``, computes line totals and the overall
    total, and returns a confirmation marked as simulated. No order record is
    stored and no order ID or creation timestamp is produced (R10.1, R10.2).

    Args:
        request: The submitted cart contents (product identifiers and
            quantities).

    Returns:
        The confirmation summary with per-item lines, the summed total, and
        ``simulated=True``.

    Raises:
        CheckoutError: If the submission is empty (server-side empty-cart
            guard, R9.5), if any quantity is not positive, or if a submitted
            ``productId`` does not resolve to a catalog product.
    """
    # Server-side re-check of the empty-cart guard (R9.5): an empty submission
    # must not be treated as a valid purchase.
    if not request.items:
        raise CheckoutError(
            code="empty_cart",
            message="Cannot confirm a simulated purchase with an empty cart.",
        )

    summary_items: list[CheckoutConfirmationItem] = []
    for item in request.items:
        if item.quantity <= 0:
            raise CheckoutError(
                code="invalid_quantity",
                message=(
                    "Each submitted item must have a quantity of at least one."
                ),
            )

        product = catalog.get_product(item.product_id)
        if product is None:
            # The submitted cart references a product that is not in the shared
            # catalog data, so a consistent summary cannot be built (R11).
            raise CheckoutError(
                code="unknown_product",
                message="A submitted item does not match a known product.",
            )

        line_total = product.price * item.quantity
        summary_items.append(
            CheckoutConfirmationItem(
                product_id=product.id,
                name=product.name,
                unit_price=product.price,
                quantity=item.quantity,
                line_total=line_total,
            )
        )

    total = sum(line.line_total for line in summary_items)

    return CheckoutConfirmation(items=summary_items, total=total, simulated=True)
