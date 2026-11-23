"""Simulated checkout logic owned by the commerce service (Stage 3 parity).

Builds a non-persistent purchase confirmation from the submitted cart. No order
is stored, no payment is processed. Error codes match Stage 3:
``empty_cart``, ``invalid_quantity``, ``unknown_product``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app import catalog


class CheckoutError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class _CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CheckoutRequestItem(_CamelModel):
    product_id: str
    quantity: int


class CheckoutRequest(_CamelModel):
    items: list[CheckoutRequestItem] = []


class CheckoutConfirmationItem(_CamelModel):
    product_id: str
    name: str
    unit_price: float
    quantity: int
    line_total: float


class CheckoutConfirmation(_CamelModel):
    items: list[CheckoutConfirmationItem] = []
    total: float
    simulated: bool = True


def confirm_checkout(request: CheckoutRequest) -> CheckoutConfirmation:
    if not request.items:
        raise CheckoutError("empty_cart", "The cart is empty.")

    confirmation_items: list[CheckoutConfirmationItem] = []
    total = 0.0
    for item in request.items:
        if item.quantity <= 0:
            raise CheckoutError(
                "invalid_quantity",
                f"Quantity for product '{item.product_id}' must be positive.",
            )
        product = catalog.get_product(item.product_id)
        if product is None:
            raise CheckoutError(
                "unknown_product",
                f"No product exists with id '{item.product_id}'.",
            )
        line_total = round(product.price * item.quantity, 2)
        total = round(total + line_total, 2)
        confirmation_items.append(
            CheckoutConfirmationItem(
                product_id=product.id,
                name=product.name,
                unit_price=product.price,
                quantity=item.quantity,
                line_total=line_total,
            )
        )

    return CheckoutConfirmation(items=confirmation_items, total=total, simulated=True)
