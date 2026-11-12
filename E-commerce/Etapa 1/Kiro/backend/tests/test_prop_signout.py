"""Property-based test for sign-out ending the session (Task 4.8).

Feature: ecommerce-stage1, Property 9: Sign-out ends the active session.

Property 9 — For any active session, performing sign-out results in a state in
which no session is active. A variety of active sessions are produced by
seeding a fresh ``AccountStore`` with a generated account, signing in to make
the session active, then signing out. The resulting session must report
``active is False`` and ``customer_id is None``, and the in-process session
state read back via ``get_current_session()`` must also be inactive.

**Validates: Requirements 6.6**
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.accounts import AccountStore
from app.services.password import hash_password
from app.services.signin_service import (
    get_current_session,
    reset_session,
    sign_in,
    sign_out,
)

# Non-blank, printable identifiers. Restricted to printable ASCII and bounded
# in length so generation stays simple; ``strip() != ""`` keeps only values the
# sign-in service treats as present (not empty/whitespace).
_identifiers = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=24,
).filter(lambda s: s.strip() != "")

# Non-blank, printable passwords. Kept short so the real one-way hash (bcrypt)
# stays fast per example while still varying across a broad input space.
_passwords = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=16,
).filter(lambda s: s.strip() != "")


# ``deadline=None`` because each example runs a real, deliberately slow one-way
# hash (bcrypt) during sign-in; its per-call cost can exceed Hypothesis's
# default per-example deadline, which makes that timing threshold inappropriate
# here. No iteration count is prescribed; the unmodified Hypothesis default
# controls the number of generated cases. The module-level session state is
# shared, so ``reset_session()`` runs before each example to guarantee a known
# starting point regardless of prior examples.
@given(identifier=_identifiers, password=_passwords)
@settings(deadline=None)
def test_sign_out_ends_the_active_session(identifier: str, password: str) -> None:
    """Signing out of any active session leaves no active session.

    Feature: ecommerce-stage1, Property 9: Sign-out ends the active session.
    Validates Requirements 6.6.
    """
    reset_session()

    # Seed a fresh store with one account and sign in so a session is active.
    store = AccountStore()
    store.create_account(identifier, hash_password(password))

    active = sign_in(identifier, password, store=store)
    assert active.active is True  # precondition: we started from an active session.

    ended = sign_out()

    # The returned session reports no active session.
    assert ended.active is False
    assert ended.customer_id is None
    # The in-process session state also reflects no active session.
    assert get_current_session().active is False
