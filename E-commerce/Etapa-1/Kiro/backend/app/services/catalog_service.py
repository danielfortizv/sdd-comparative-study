"""Catalog retrieval service (service layer).

This service exposes the catalog business operations the API layer depends on.
It returns the shared demonstration product data read from the data-access
layer, keeping product identity, name, and price consistent across the whole
journey (Requirements 1.1, 1.3, 1.5, 11.1). It contains no HTTP concerns: the
API layer maps the results to responses and status codes.
"""

from __future__ import annotations

from app.data import catalog as catalog_data
from app.models.product import Product


class ProductNotFoundError(Exception):
    """Raised when a requested product id does not exist in the catalog.

    The API layer catches this and maps it to a structured 404 JSON response
    (Requirements 1.4). The offending id is carried so the message can name it
    without exposing internal detail or stack traces.
    """

    def __init__(self, product_id: str) -> None:
        self.product_id = product_id
        super().__init__(f"Product not found: {product_id}")


def list_products() -> list[Product]:
    """Return all catalog products as the shared demonstration data.

    This is the single source used across catalog, cart, and checkout so the
    product identity, name, and price stay consistent (Requirements 1.5, 11.1).
    """
    return catalog_data.list_products()


def get_product(product_id: str) -> Product:
    """Return the product with the given id.

    Args:
        product_id: The stable product identity to resolve.

    Returns:
        The matching :class:`Product`.

    Raises:
        ProductNotFoundError: If no product has the given id.
    """
    product = catalog_data.get_product(product_id)
    if product is None:
        raise ProductNotFoundError(product_id)
    return product
