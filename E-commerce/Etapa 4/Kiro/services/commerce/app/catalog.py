"""Static catalog fixture owned by the commerce service.

Identical demonstration products to Stage 1-3 so product identity, name, and
price stay consistent across catalog, cart, and checkout. Immutable, so it
needs no table.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Product(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    id: str
    name: str
    image_url: str
    description: str
    price: float
    available: bool = True


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
    return [p.model_copy() for p in _CATALOG]


def get_product(product_id: str) -> Product | None:
    for product in _CATALOG:
        if product.id == product_id:
            return product.model_copy()
    return None
