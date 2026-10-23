"""Requirement 4 error-case and boundary-length API tests (task 5.2).

Exercises the Evaluate_Endpoint through the FastAPI TestClient, asserting that
each error case returns an `ErrorResponse` (an `error` field, no `result`)
with a 4xx status, and that expression length boundaries (1 and 256 accepted,
257 rejected) behave per the contract.

_Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 5.2, 5.6, 15.2_
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _post(expression: str) -> object:
    return client.post('/api/v1/evaluate', json={'expression': expression})


# --------------------------------------------------------------------------- #
# Requirement 4 error cases -> 4xx ErrorResponse, no result (4.1-4.6)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    'expression',
    [
        '1 / 0',          # division by zero (4.1)
        '3 + * 4',        # invalid operator sequence (4.2)
        '(1 + 2',         # unclosed parenthesis (4.3)
        '2 & 3',          # invalid character (4.4)
        '   ',            # whitespace-only / empty (4.5)
    ],
)
def test_error_cases_return_4xx_with_error_and_no_result(expression: str) -> None:
    response = _post(expression)
    assert 400 <= response.status_code < 500
    body = response.json()
    assert 'error' in body
    assert isinstance(body['error'], str) and body['error']
    assert 'result' not in body


def test_division_by_zero_message_is_descriptive() -> None:
    body = _post('1 / 0').json()
    assert 'division' in body['error'].lower() or 'zero' in body['error'].lower()


def test_empty_expression_rejected_by_schema() -> None:
    # An empty string violates the min_length=1 schema constraint -> 4xx.
    response = client.post('/api/v1/evaluate', json={'expression': ''})
    assert 400 <= response.status_code < 500
    assert 'result' not in response.json()


# --------------------------------------------------------------------------- #
# Boundary lengths (Requirements 5.2, 5.6, 1.5)
# --------------------------------------------------------------------------- #
def test_length_one_accepted() -> None:
    response = _post('7')
    assert response.status_code == 200
    body = response.json()
    assert body['result'] == '7'
    assert 'error' not in body


def test_length_256_accepted() -> None:
    # A chain of '+1' additions keeps the value small (within the evaluator's
    # precision) while reaching the maximum length. '1' + 127*'+1' = 255 chars;
    # a trailing space (skipped as whitespace) pads it to exactly 256.
    expression = '1' + ('+1' * 127) + ' '
    assert len(expression) == 256
    response = _post(expression)
    assert response.status_code == 200
    body = response.json()
    assert body['result'] == '128'
    assert 'error' not in body


def test_length_257_rejected() -> None:
    expression = '1' + ('+1' * 128)  # 1 + 256 = 257 chars
    assert len(expression) == 257
    response = _post(expression)
    assert 400 <= response.status_code < 500
    assert 'result' not in response.json()


# --------------------------------------------------------------------------- #
# Success response shape (Requirement 5.5 support)
# --------------------------------------------------------------------------- #
def test_success_has_result_and_no_error() -> None:
    body = _post('2 + 3').json()
    assert body == {'result': '5'}
