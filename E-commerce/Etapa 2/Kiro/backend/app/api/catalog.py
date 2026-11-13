"""Catalog API router (API layer).

Exposes the read-only catalog endpoints over HTTP/JSON:

* ``GET /products`` - list all catalog products (no authentication required).
* ``GET /products/{product_id}`` - retrieve a single product for the expanded
  view.

Both endpoints return the shared demonstration product data so the catalog,
cart, and checkout stay consistent (Requirements 1.1, 1.3, 1.4, 1.5, 11.1).
Unknown ids produce a structured JSON error with a 404 status code and no
stack trace or internal diagnostics, matching the design's Error Handling.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.product import Product
from app.services import catalog_service
from app.services.catalog_service import ProductNotFoundError

router = APIRouter(tags=["catalog"])


@router.get("/products", response_model=list[Product])
def list_products() -> list[Product]:
    """Return the full catalog product list.

    Reachable without authentication (Requirement 1.1). Serves the same
    demonstration data used across the rest of the flow (Requirements 1.3,
    1.5, 11.1).
    """
    return catalog_service.list_products()


@router.get("/products/{product_id}", response_model=Product)
def get_product(product_id: str) -> Product:
    """Return a single product for the expanded view (Requirement 1.4).

    Raises a structured 404 error when the id is unknown. The response body
    carries only a safe, client-facing message (no stack trace or internal
    detail), per the design's Error Handling.
    """
    try:
        return catalog_service.get_product(product_id)
    except ProductNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "product_not_found",
                "message": f"No product exists with id '{product_id}'.",
                "productId": product_id,
            },
        )
