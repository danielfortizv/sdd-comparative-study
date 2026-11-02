"""Property-based API tests P6 and P7 (task 6.6).

P6: every Evaluate_Endpoint response is an unambiguous success-XOR-error
discriminated union with the correct HTTP status. P7: any expression longer
than 256 characters is rejected with a 4xx and no result.
"""

from __future__ import annotations

from hypothesis import given
from fastapi.testclient import TestClient

from app.main import app
from tests.properties.strategies import (
    PROPERTY_SETTINGS,
    asts,
    render,
    over_length_expressions,
    expressions_with_invalid_character,
    zero_divisor_expressions,
)
import hypothesis.strategies as st

client = TestClient(app)


# Feature: web-calculator, Property 6: Response shape is an unambiguous success-XOR-error discriminated union
@PROPERTY_SETTINGS
@given(
    expression=st.one_of(
        asts().map(render),
        zero_divisor_expressions(),
        expressions_with_invalid_character(),
    )
)
def test_p6_response_is_success_xor_error(expression: str) -> None:
    """Exactly one of result/error is present, with a matching status.

    Validates: Requirements 4.6, 5.3, 5.4, 5.5
    """
    response = client.post("/api/v1/evaluate", json={"expression": expression})
    body = response.json()
    has_result = "result" in body
    has_error = "error" in body
    # Exactly one of the two fields is present (never both, never neither).
    assert has_result != has_error
    if has_result:
        assert response.status_code == 200
        assert isinstance(body["result"], str)
    else:
        assert 400 <= response.status_code < 500
        assert isinstance(body["error"], str) and body["error"]


# Feature: web-calculator, Property 7: Expressions exceeding the length limit are rejected
@PROPERTY_SETTINGS
@given(expression=over_length_expressions(256))
def test_p7_over_length_rejected(expression: str) -> None:
    """Any expression > 256 chars is rejected with a 4xx and no result.

    Validates: Requirements 1.5, 5.6
    """
    assert len(expression) > 256
    response = client.post("/api/v1/evaluate", json={"expression": expression})
    assert 400 <= response.status_code < 500
    assert "result" not in response.json()
