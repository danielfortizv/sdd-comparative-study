"""Property-based test for the register-then-sign-in round trip.

Feature: ecommerce-stage1, Property 10: Register-then-sign-in establishes a
session (round trip).

Property 10 states that registering with valid credentials and then signing in
with the same credentials establishes an active session for that customer:
given a non-empty, conforming identifier and password, ``register`` creates a
``Customer`` and a subsequent ``sign_in`` with the identical credentials
returns an active ``Session`` whose ``customer_id`` is that Customer's id.

**Validates: Requirements 6.9**
"""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.data.accounts import AccountStore
from app.services.registration_service import register
from app.services.signin_service import reset_session, sign_in

# Conforming credential values: non-empty text that is not whitespace-only.
# Values are kept short and printable so bcrypt hashing (performed by both
# register and sign_in) stays fast across many generated examples. ``.filter``
# drops whitespace-only values, which the services treat as empty/non-conforming
# input rather than valid credentials.
_conforming_text = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=24,
).filter(lambda value: value.strip() != "")


# bcrypt hashing is deliberately slow (~0.2s per call) and happens on both the
# register and sign_in legs of each example, so per-example timing is not
# meaningful here: the deadline is disabled (and the slow-example health check
# suppressed) because real one-way hashing makes Hypothesis's per-example timing
# threshold inappropriate. No iteration count is prescribed; the unmodified
# Hypothesis default controls the number of generated cases.
@settings(
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
@given(identifier=_conforming_text, password=_conforming_text)
def test_register_then_sign_in_establishes_active_session(
    identifier: str, password: str
) -> None:
    """Registering then signing in with the same credentials opens a session."""
    # Fresh store per example so register and sign_in share one account space,
    # and a known-inactive session so the assertion reflects this round trip.
    store = AccountStore()
    reset_session()

    customer = register(identifier, password, store=store)

    session = sign_in(identifier, password, store=store)

    # The same credentials establish an active session for that customer (R6.9).
    assert session.active is True
    assert session.customer_id == customer.id
