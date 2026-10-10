"""Unit tests for the catalog data-access layer.

These tests exercise ``app.data.catalog`` (fixed in-memory product data) and
confirm that catalog retrieval returns the shared demonstration product data
consistently and immutably. The data retrieved by ``list_products`` and
``get_product`` is the single source used across the rest of the Application
flow (Requirement 1.5).
"""

from __future__ import annotations

from app.data import catalog
from app.models.product import Product


def test_list_products_returns_all_catalog_entries() -> None:
    products = catalog.list_products()

    assert isinstance(products, list)
    assert len(products) == 6
    assert all(isinstance(product, Product) for product in products)


def test_list_products_have_unique_ids() -> None:
    products = catalog.list_products()

    ids = [product.id for product in products]
    assert len(ids) == len(set(ids))


def test_get_product_returns_matching_product() -> None:
    product = catalog.get_product("p-001")

    assert product is not None
    assert product.id == "p-001"
    assert product.name == "Wireless Headphones"
    assert product.price == 79.99
    assert product.available is True


def test_get_product_returns_none_for_unknown_id() -> None:
    assert catalog.get_product("does-not-exist") is None


def test_get_product_matches_entry_from_list_products() -> None:
    """get_product resolves the same demonstration data shown in the list.

    Catalog, cart, and checkout all resolve products from this data, so the
    identity, name, and price retrieved by id must equal the entry in the
    full list (Requirement 1.5).
    """
    listed = {product.id: product for product in catalog.list_products()}

    for product_id, expected in listed.items():
        retrieved = catalog.get_product(product_id)
        assert retrieved is not None
        assert retrieved.id == expected.id
        assert retrieved.name == expected.name
        assert retrieved.price == expected.price
        assert retrieved.image_url == expected.image_url
        assert retrieved.description == expected.description
        assert retrieved.available == expected.available


def test_list_products_returns_fresh_copies_each_call() -> None:
    """Callers receive copies, so the shared fixed catalog stays immutable."""
    first = catalog.list_products()
    first[0].name = "Mutated Name"
    first[0].price = 0.0

    second = catalog.list_products()
    assert second[0].name != "Mutated Name"
    assert second[0].price != 0.0


def test_get_product_returns_fresh_copy_each_call() -> None:
    """Mutating a retrieved product must not affect the shared catalog data."""
    product = catalog.get_product("p-002")
    assert product is not None
    product.price = 0.0

    again = catalog.get_product("p-002")
    assert again is not None
    assert again.price == 119.50
