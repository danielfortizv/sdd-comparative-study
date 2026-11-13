"""Property-based test for registration validation.

Feature: ecommerce-stage1, Property 5: Registration validation rejects and
identifies all offending fields.

Validates: Requirements 5.3, 5.4

Property 5 states: for any registration submission in which some required
items are empty and/or some do not conform to their expected format, the
submission is rejected and the reported set of offending items equals exactly
the set of items that are empty or non-conforming.

The required items of the credential contract are ``identifier`` and
``password`` (Requirement 5.1). An item is empty when it is ``None`` or a
whitespace-only string (Requirement 5.3); an item is non-conforming when it is
present but not a text value (Requirement 5.4). An item is never both.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.data.accounts import AccountStore
from app.services.registration_service import RegistrationError, register

# A field in the submission can take one of three classifications. The
# generators below produce values that fall squarely into exactly one class so
# the expected offending sets are known for every example.

# Valid: a present, non-empty text value (conforms to the expected format).
_valid_values = st.text(min_size=1).filter(lambda s: s.strip() != "")

# Empty: None, or a string that is empty or only whitespace (Requirement 5.3).
_empty_values = st.one_of(
    st.none(),
    st.sampled_from(["", " ", "   ", "\t", "\n", " \t\n "]),
    st.text(alphabet=" \t\n\r\f\v", min_size=0, max_size=5),
)

# Non-conforming: present but not a text value (Requirement 5.4).
_non_conforming_values = st.one_of(
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.booleans(),
    st.lists(st.integers(), max_size=3),
    st.dictionaries(st.text(max_size=3), st.integers(), max_size=3),
)


@st.composite
def _submissions(draw: st.DrawFn) -> tuple[object, object, set[str], set[str]]:
    """Build a submission with at least one offending field.

    Returns the ``identifier`` and ``password`` values to submit along with the
    expected set of empty field names and the expected set of non-conforming
    field names, derived directly from how each value was drawn.
    """
    # For each required field choose one of: valid, empty, non-conforming.
    classes = draw(
        st.lists(
            st.sampled_from(["valid", "empty", "non_conforming"]),
            min_size=2,
            max_size=2,
        )
    )
    # Require at least one offending field so the property's premise holds.
    if classes[0] == "valid" and classes[1] == "valid":
        classes[draw(st.integers(min_value=0, max_value=1))] = draw(
            st.sampled_from(["empty", "non_conforming"])
        )

    field_names = ("identifier", "password")
    values: list[object] = []
    expected_empty: set[str] = set()
    expected_non_conforming: set[str] = set()

    for name, cls in zip(field_names, classes):
        if cls == "valid":
            values.append(draw(_valid_values))
        elif cls == "empty":
            values.append(draw(_empty_values))
            expected_empty.add(name)
        else:  # non_conforming
            values.append(draw(_non_conforming_values))
            expected_non_conforming.add(name)

    return values[0], values[1], expected_empty, expected_non_conforming


# Feature: ecommerce-stage1, Property 5: Registration validation rejects and
# identifies all offending fields
@given(_submissions())
def test_registration_identifies_exactly_the_offending_fields(
    submission: tuple[object, object, set[str], set[str]],
) -> None:
    identifier, password, expected_empty, expected_non_conforming = submission

    # A fresh store per example keeps examples independent (R5.6 side effects).
    store = AccountStore()

    try:
        register(identifier, password, store=store)
    except RegistrationError as error:
        # The submission is rejected, and the reported sets of offending items
        # equal exactly the empty set and the non-conforming set.
        assert set(error.empty_fields) == expected_empty
        assert set(error.non_conforming_fields) == expected_non_conforming
        # An item is never reported as both empty and non-conforming.
        assert not (set(error.empty_fields) & set(error.non_conforming_fields))
    else:
        raise AssertionError(
            "Expected the submission to be rejected because it contains "
            "empty and/or non-conforming required items."
        )
