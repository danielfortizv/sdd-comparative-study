"""Product data model (backend-owned, served to the frontend).

A ``Product`` represents an item offered in the catalog. The same product
identity is used across catalog, cart, and checkout so the journey stays
consistent (Requirements 1.3, 1.5, 11). Field names are serialized in
camelCase (for example ``imageUrl``) to match the HTTP/JSON interface
described in the design, while Python identifiers remain snake_case.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class Product(BaseModel):
    """An item offered in the catalog.

    Attributes:
        id: Stable product identity used across catalog, cart, and checkout.
        name: Product name.
        image_url: One representative image (serialized as ``imageUrl``).
        description: Short description text.
        price: Unit price in the demonstration currency.
        available: General availability indication.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str
    name: str
    image_url: str
    description: str
    price: float
    available: bool = Field(default=True)
