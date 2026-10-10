"""Property-based test for password storage (Task 4.5).

Feature: ecommerce-stage1, Property 12: Passwords are not stored as readable
plain text.

Property 12 — For any password used to register an account, the stored
credential representation is not the readable plain-text password: the stored
``Customer.password_hash`` neither equals the plain-text password nor contains
it as a substring. This is exercised against a fresh in-memory ``AccountStore``
per example, through ``registration_service.register``.

**Validates: Requirements 7.3**
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.accounts import AccountStore
from app.services.registration_service import register

# Non-empty, conforming plain-text passwords. Restricted to reasonable
# printable text (and bounded in length) so the real one-way hash stays fast
# while still covering a broad space of inputs. ``strip() != ""`` keeps only
# values the service treats as present and conforming (not empty/whitespace).
#
# A minimum length of 8 makes the "not a substring of the hash" assertion
# meaningful: a bcrypt hash is a ~60-char string drawn from a small alphabet,
# so a 1-2 character password can appear inside it purely by coincidence
# without the password being stored. That coincidence does not indicate
# plain-text storage, so we generate passwords long and distinctive enough
# that a coincidental embedding is vanishingly unlikely, while still probing
# the real property of Requirement 7.3.
_passwords = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=8,
    max_size=48,
).filter(lambda s: s.strip() != "")


# ``deadline=None`` because each example runs a real, deliberately slow one-way
# hash (bcrypt), whose cost per call can exceed Hypothesis's default per-example
# deadline, which makes that timing threshold inappropriate here. The slowness
# is the intended security property, not a defect. No iteration count is
# prescribed; the unmodified Hypothesis default controls the number of
# generated cases.
@given(password=_passwords)
@settings(deadline=None)
def test_stored_password_is_never_readable_plain_text(password: str) -> None:
    """The stored credential never exposes the readable plain-text password.

    Feature: ecommerce-stage1, Property 12: Passwords are not stored as
    readable plain text. Validates Requirements 7.3.
    """
    store = AccountStore()

    customer = register("account-identifier", password, store=store)

    # The stored representation must not be the plain-text password, either as
    # an exact value or embedded as a substring.
    assert customer.password_hash != password
    assert password not in customer.password_hash
