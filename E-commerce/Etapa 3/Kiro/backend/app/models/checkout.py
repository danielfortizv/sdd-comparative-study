"""Checkout data models (non-persistent request/response for the simulated purchase).

These models describe the HTTP/JSON contract for ``POST /checkout/confirm``
(Requirement 10). A ``CheckoutRequest`` carries only the submitted cart
contents (product identifiers and quantities); the backend resolves product
details (name, unit price) from the shared catalog data so product information
stays consistent across the journey (Requirements 10.2, 11). The
``CheckoutConfirmation`` is the summary returned for a completed
Simulated_Purchase: it is built from the submitted cart and catalog data, is
never stored, and carries no order identity and no creation timestamp
(Requirements 10.1, 10.2).

Field names are serialized in camelCase (for example ``productId``,
``unitPrice``, ``lineTotal``) to match the HTTP/JSON interface, while Python
identifiers remain snake_case.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    """Base model serializing fields in camelCase for the HTTP/JSON interface."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class CheckoutRequestItem(_CamelModel):
    """A single submitted cart line: a product identity and its quantity.

    Attributes:
        product_id: References ``Product.id`` (shared identity, R11).
        quantity: Count of this product in the submitted cart.
    """

    product_id: str
    quantity: int


class CheckoutRequest(_CamelModel):
    """The cart contents submitted for a Simulated_Purchase (R10).

    Carries only product identifiers and quantities; the backend resolves
    product details from catalog data.

    Attributes:
        items: The submitted cart contents.
    """

    items: list[CheckoutRequestItem]


class CheckoutConfirmationItem(_CamelModel):
    """A purchased-items summary line, resolved from the catalog (R10.2, R11).

    Attributes:
        product_id: Stable product identity (shared across the journey).
        name: Product name resolved from catalog data.
        unit_price: Unit price resolved from catalog data.
        quantity: Count of this product in the purchase.
        line_total: ``unit_price * quantity``.
    """

    product_id: str
    name: str
    unit_price: float
    quantity: int
    line_total: float


class CheckoutConfirmation(_CamelModel):
    """The confirmation summary returned for a completed Simulated_Purchase.

    Built from the submitted cart and catalog data and not stored. It carries
    no order identity and no creation timestamp (R10.1, R10.2).

    Attributes:
        items: The purchased-items summary.
        total: Purchased total, equal to the sum of ``line_total`` across items
            (consistent with the cart, R11.5).
        simulated: Always ``True`` — the purchase is fictitious (R10.1).
    """

    items: list[CheckoutConfirmationItem]
    total: float
    simulated: Literal[True] = True
