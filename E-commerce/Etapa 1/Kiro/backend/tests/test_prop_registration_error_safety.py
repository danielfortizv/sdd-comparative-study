"""Property-based test for registration error message safety.

Feature: ecommerce-stage1, Property 6: Registration error messages exclude
submitted credential values

For any rejected registration submission, the displayed error message contains
none of the credential values that were submitted. This exercises the
registration service logic directly against a fresh in-memory account store per
example, covering the three ways a submission is rejected: an empty/whitespace
required item, a non-conforming (non-text) item, and a duplicate identifier
conflict. Only non-empty submitted VALUES are meaningful to leak, so the
assertion checks that each non-empty submitted credential value is absent from
the error message text.

Validates: Requirements 5.5
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.accounts import AccountStore
from app.services.registration_service import (
    IdentifierTakenError,
    RegistrationError,
    register,
)

# Non-empty text values that, after trimming, still have characters. These are
# the submitted values that would be meaningful to leak if echoed back. A fixed
# sentinel prefix that never occurs in the service's fixed error templates
# (e.g. "Required field(s) missing: ...", "... must be text") is prepended so a
# match unambiguously means the submitted value was echoed back, rather than a
# short random value coincidentally overlapping static message copy such as the
# "(s)" in "field(s)". The random suffix still ranges over arbitrary text to
# exercise the credential input space.
_nonempty_text = st.text(min_size=1).map(
    lambda suffix: f"submitted-value-sentinel-\u2764-{suffix}"
)

# Whitespace-only / empty text is treated as an empty required item by the
# service and is trivially not a meaningful value to leak.
_empty_text = st.sampled_from(["", " ", "   ", "\t", "\n", "  \t "])

# A present-but-non-conforming value: anything that is not text (and not None).
_non_conforming = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.lists(st.integers(), max_size=3),
)


def _submitted_values(identifier: object, password: object) -> list[str]:
    """Return the submitted credential values that are non-empty text.

    Only these are meaningful to check for leakage: empty/whitespace values are
    trivially absent-or-present and non-text values are not credential strings a
    user would recognize being echoed.
    """
    values: list[str] = []
    for value in (identifier, password):
        if isinstance(value, str) and value.strip() != "":
            values.append(value)
    return values


@settings(deadline=None)
@given(
    identifier=st.one_of(_nonempty_text, _empty_text, _non_conforming),
    password=st.one_of(_nonempty_text, _empty_text, _non_conforming),
)
def test_registration_error_excludes_submitted_credential_values(
    identifier: object, password: object
) -> None:
    # Feature: ecommerce-stage1, Property 6: Registration error messages
    # exclude submitted credential values
    store = AccountStore()

    both_nonempty_text = (
        isinstance(identifier, str)
        and identifier.strip() != ""
        and isinstance(password, str)
        and password.strip() != ""
    )

    if both_nonempty_text:
        # A fully valid submission would be accepted. To still produce a
        # rejection for the property, pre-create the account so the second
        # attempt is a duplicate-identifier conflict. The submitted values
        # (identifier + password) must not appear in the conflict message.
        register(identifier, "pre-existing-hash-seed", store=store)
        try:
            register(identifier, password, store=store)
        except IdentifierTakenError as error:
            message = error.message
        else:
            raise AssertionError(
                "Expected a duplicate-identifier rejection but registration "
                "succeeded."
            )
    else:
        # At least one item is empty/whitespace or non-conforming, so the
        # submission is rejected by validation.
        try:
            register(identifier, password, store=store)
        except RegistrationError as error:
            message = error.message
        else:
            raise AssertionError(
                "Expected a validation rejection but registration succeeded."
            )

    # The displayed error message must contain none of the non-empty submitted
    # credential values (Requirement 5.5).
    for value in _submitted_values(identifier, password):
        assert value not in message, (
            "Submitted credential value leaked into the registration error "
            f"message: {value!r} appeared in {message!r}"
        )
