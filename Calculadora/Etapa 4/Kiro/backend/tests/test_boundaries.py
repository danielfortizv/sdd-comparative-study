"""Stage 3 boundary-success and overflow edge-case tests (task 41.3).

28.4: asin/acos at |x| == 1 succeed with a calculated result (no error).
28.7: an arithmetic operation producing a non-finite result through overflow is
rejected with a 4xx ErrorResponse and no result.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _post(expression: str, angle_mode: str = "radians") -> object:
    return client.post(
        "/api/v1/evaluate",
        json={"expression": expression, "angle_mode": angle_mode},
    )


# 28.4 inverse-trig at |x| == 1 succeeds ------------------------------------ #
@pytest.mark.parametrize(
    ("expression", "angle_mode"),
    [
        ("asin(1)", "degrees"),
        ("asin(-1)", "degrees"),
        ("acos(1)", "degrees"),
        ("acos(-1)", "degrees"),
        ("asin(1)", "radians"),
        ("acos(1)", "radians"),
    ],
)
def test_inverse_trig_at_boundary_one_succeeds(
    expression: str, angle_mode: str
) -> None:
    response = _post(expression, angle_mode)
    assert response.status_code == 200
    body = response.json()
    assert "result" in body
    assert "error" not in body


def test_acos_one_is_zero_boundary() -> None:
    # Regression guard for defect D-01: acos(1) == 0, not 90 degrees.
    body = _post("acos(1)", "degrees").json()
    assert body["result"] == "0"


# 28.7 overflow -> non-finite -> 4xx, no result ----------------------------- #
@pytest.mark.parametrize(
    "expression",
    [
        "9 ^ 9 ^ 9",          # a tower that overflows the decimal context
        "10 ^ 10 ^ 10",
    ],
)
def test_overflow_rejected_with_4xx(expression: str) -> None:
    response = _post(expression)
    assert 400 <= response.status_code < 500
    assert "result" not in response.json()
