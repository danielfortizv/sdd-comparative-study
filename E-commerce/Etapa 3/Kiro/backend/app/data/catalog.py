"""Fixed in-memory catalog data (data-access layer).

This module holds the demonstration product data as fixed in-memory values and
exposes read-only access to it. The same data is used across catalog, cart,
and checkout so product identity, name, and price stay consistent through the
journey (Requirements 1.3, 1.5). Nothing here is mutated at runtime: the
catalog is a demonstration fixture, not a managed store.
"""

from __future__ import annotations

from app.models.product import Product

# Fixed demonstration catalog. Prices use the demonstration currency implied by
# this data; no multi-currency support is modeled. Identifiers are stable so
# the cart and checkout can resolve the same product across views.
_CATALOG: tuple[Product, ...] = (
    Product(
        id="p-001",
        name="Wireless Headphones",
        image_url="https://picsum.photos/seed/headphones/400/400",
        description="Over-ear wireless headphones with noise isolation.",
        price=79.99,
        available=True,
    ),
    Product(
        id="p-002",
        name="Mechanical Keyboard",
        image_url="https://picsum.photos/seed/keyboard/400/400",
        description="Compact mechanical keyboard with tactile switches.",
        price=119.50,
        available=True,
    ),
    Product(
        id="p-003",
        name="USB-C Hub",
        image_url="https://picsum.photos/seed/usbhub/400/400",
        description="Seven-in-one USB-C hub with HDMI and card reader.",
        price=42.00,
        available=True,
    ),
    Product(
        id="p-004",
        name="Ergonomic Mouse",
        image_url="https://picsum.photos/seed/mouse/400/400",
        description="Vertical ergonomic mouse designed for all-day comfort.",
        price=34.95,
        available=True,
    ),
    Product(
        id="p-005",
        name="27-inch Monitor",
        image_url="https://picsum.photos/seed/monitor/400/400",
        description="27-inch QHD monitor with a thin-bezel design.",
        price=289.00,
        available=False,
    ),
    Product(
        id="p-006",
        name="Laptop Stand",
        image_url="https://picsum.photos/seed/stand/400/400",
        description="Adjustable aluminum laptop stand for better posture.",
        price=49.99,
        available=True,
    ),
)


def list_products() -> list[Product]:
    """Return all catalog products.

    Returns a fresh list of copies so callers cannot mutate the shared fixed
    catalog data.
    """
    return [product.model_copy() for product in _CATALOG]


def get_product(product_id: str) -> Product | None:
    """Return the product with the given id, or ``None`` if it does not exist.

    Returns a copy so the shared catalog data stays immutable to callers.
    """
    for product in _CATALOG:
        if product.id == product_id:
            return product.model_copy()
    return None
