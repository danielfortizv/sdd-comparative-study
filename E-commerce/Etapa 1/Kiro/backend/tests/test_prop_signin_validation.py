"""Property-based test for sign-in validation.

Feature: ecommerce-stage1, Property 8: Sign-in validation rejects incomplete
or invalid input.

Validates: Requirements 6.3

Property 8 states: incomplete or invalid sign-in input is rejected with a
problem indicating the incomplete or invalid input.

The credential contract for sign-in is ``identifier`` + ``password``
(Requirement 6.1). ``sign_in`` treats input as:

- incomplete when the ``identifier`` or ``password`` is blank: a non-string
  value, or a string that is empty or only whitespace (``_is_blank``); and
- invalid when the ``identifier`` is not a known account (here, against a
  fresh empty ``AccountStore`` no identifier exists, so any complete input is
  invalid).

In every such case ``sign_in`` must raise ``AuthenticationError``, the problem
that indicates the incomplete or invalid input.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.data.accounts import AccountStore
from app.services.signin_service import AuthenticationError, sign_in

# Blank values: either a whitespace-only / empty string or a non-string value.
# These make a credential field "incomplete" per ``_is_blank`` (Requirement 6.3).
_blank_values = st.one_of(
    st.none(),
    st.sampled_from(["", " ", "   ", "\t", "\n", " \t\n "]),
    st.text(alphabet=" \t\n\r\f\v", min_size=0, max_size=5),
    st.integers(),
    st.booleans(),
)

# Present text values: non-blank strings suitable for a complete credential.
_present_values = st.text(min_size=1).filter(lambda s: s.strip() != "")


@st.composite
def _incomplete_inputs(draw: st.DrawFn) -> tuple[object, object]:
    """Build sign-in input in which at least one field is blank (incomplete)."""
    # Decide which fields are blank; require at least one blank field so the
    # input is genuinely incomplete.
    identifier_blank = draw(st.booleans())
    password_blank = draw(st.booleans())
    if not identifier_blank and not password_blank:
        # Force at least one field blank.
        if draw(st.booleans()):
            identifier_blank = True
        else:
            password_blank = True

    identifier = draw(_blank_values) if identifier_blank else draw(_present_values)
    password = draw(_blank_values) if password_blank else draw(_present_values)
    return identifier, password


# Feature: ecommerce-stage1, Property 8: Sign-in validation rejects incomplete
# or invalid input
@given(_incomplete_inputs())
def test_sign_in_rejects_incomplete_input(submission: tuple[object, object]) -> None:
    identifier, password = submission

    # A fresh, empty store per example keeps examples independent.
    store = AccountStore()

    try:
        sign_in(identifier, password, store=store)  # type: ignore[arg-type]
    except AuthenticationError:
        # Incomplete input is rejected with the authentication problem.
        pass
    else:
        raise AssertionError(
            "Expected incomplete sign-in input (a blank identifier and/or "
            "password) to be rejected with AuthenticationError."
        )


# Feature: ecommerce-stage1, Property 8: Sign-in validation rejects incomplete
# or invalid input
@given(identifier=_present_values, password=_present_values)
def test_sign_in_rejects_invalid_input(identifier: str, password: str) -> None:
    # A fresh, empty store means no account exists for any identifier, so every
    # complete submission is invalid (unknown identifier) and must be rejected.
    store = AccountStore()

    try:
        sign_in(identifier, password, store=store)
    except AuthenticationError:
        # Invalid input (unknown identifier) is rejected with the problem.
        pass
    else:
        raise AssertionError(
            "Expected invalid sign-in input (an identifier that is not a known "
            "account) to be rejected with AuthenticationError."
        )
