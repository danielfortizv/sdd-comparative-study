"""Property-based test for confirmation summary and total derivation.

Feature: ecommerce-stage1, Property 16: Confirmation summary and total are
derived from the submitted cart and catalog data.

Property 16 states that, for any non-empty cart, the confirmation's items
(identity, name, unit price, quantity, line total) and total are derived from
the submitted cart and the shared catalog data, with the total equal to the
sum of line totals. This test exercises ``confirm_checkout`` over many
randomly generated carts that reference existing catalog product ids with
positive integer quantities, and asserts that each confirmation line resolves
its name and unit price from the catalog, that ``line_total == unit_price *
quantity``, that the overall ``total`` equals the sum of line totals, and that
the confirmation is marked ``simulated``.

**Validates: Requirements 10.2**
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.data import catalog
from app.models.checkout import CheckoutRequest, CheckoutRequestItem
from app.services.checkout_service import confirm_checkout

# All catalog product ids: the input space for a submitted cart is any
# non-empty sequence of these ids paired with positive integer quantities.
_PRODUCT_IDS: list[str] = [product.id for product in catalog.list_products()]

# A single submitted cart line: an existing product id with a positive
# quantity. Quantities are bounded to a reasonable range to keep generation
# meaningful; the service treats each line independently, so duplicate product
# ids across lines are allowed and intentionally not deduplicated here.
# Build via explicit keyword args (not ``st.builds``) so the camelCase alias
# does not shadow the ``product_id`` field during construction.
_cart_item = st.builds(
    lambda product_id, quantity: CheckoutRequestItem(
        product_id=product_id, quantity=quantity
    ),
    product_id=st.sampled_from(_PRODUCT_IDS),
    quantity=st.integers(min_value=1, max_value=100),
)

# A non-empty submitted cart.
_cart = st.lists(_cart_item, min_size=1, max_size=12)


@given(items=_cart)
def test_confirmation_derives_summary_and_total_from_catalog(
    items: list[CheckoutRequestItem],
) -> None:
    """Confirmation lines and total derive from the cart and catalog data."""
    request = CheckoutRequest(items=items)

    confirmation = confirm_checkout(request)

    # The confirmation is a Simulated_Purchase (R10.1).
    assert confirmation.simulated is True

    # One confirmation line per submitted cart line, in the same order, each
    # carrying the submitted identity and quantity.
    assert len(confirmation.items) == len(items)
    for submitted, line in zip(items, confirmation.items):
        product = catalog.get_product(submitted.product_id)
        assert product is not None

        # Identity and quantity come straight from the submitted cart.
        assert line.product_id == submitted.product_id
        assert line.quantity == submitted.quantity

        # Name and unit price are resolved from the catalog data.
        assert line.name == product.name
        assert line.unit_price == product.price

        # Line total is derived: unit price times quantity.
        assert line.line_total == product.price * submitted.quantity

    # The overall total equals the sum of the line totals (R10.2).
    assert confirmation.total == sum(line.line_total for line in confirmation.items)
