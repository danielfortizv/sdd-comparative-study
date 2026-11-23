"""Property-based test for valid registration creating an account.

Feature: ecommerce-stage1, Property 7: Valid, conforming registration creates
an account.

Property 7 states that any fully present, conforming registration submission
creates an account: given a non-empty, conforming (non-whitespace) identifier
and password, ``register`` creates a ``Customer`` and persists it in the
account store so the account becomes retrievable.

**Validates: Requirements 5.6**
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.data.accounts import AccountStore
from app.models.customer import Customer
from app.services.registration_service import register

# Conforming credential values: non-empty text that is not whitespace-only.
# Passwords are kept to reasonable printable text so bcrypt hashing stays fast
# across many generated examples. ``.filter`` drops whitespace-only values,
# which the service treats as empty (and therefore non-conforming inputs).
_conforming_text = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=50,
).filter(lambda value: value.strip() != "")


# bcrypt hashing is deliberately slow (~0.2s per call), so per-example timing is
# not meaningful here: the deadline is disabled (and the slow-example health
# check suppressed) because real one-way hashing makes Hypothesis's per-example
# timing threshold inappropriate. No iteration count is prescribed; the
# unmodified Hypothesis default controls the number of generated cases.
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(identifier=_conforming_text, password=_conforming_text)
def test_valid_conforming_registration_creates_account(
    identifier: str, password: str
) -> None:
    """A fully present, conforming submission always creates an account."""
    store = AccountStore()

    customer = register(identifier, password, store=store)

    # register returns a Customer carrying the submitted identifier.
    assert isinstance(customer, Customer)
    assert customer.identifier == identifier

    # The account was created and is retrievable from the store (R5.6).
    assert store.has_account(identifier) is True
    retrieved = store.get_by_identifier(identifier)
    assert retrieved is not None
    assert retrieved.identifier == identifier
