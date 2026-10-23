"""Domain-error and angle-mode API tests (task 26.2).

25.4: each scientific Domain_Error returns a 4xx ErrorResponse with no result.
17.9/17.10/24.3/24.4: angle mode defaults to radians when omitted; an invalid
angle mode is rejected with a descriptive 4xx.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _post(expression: str, angle_mode: str | None = None) -> object:
    body: dict = {"expression": expression}
    if angle_mode is not None:
        body["angle_mode"] = angle_mode
    return client.post("/api/v1/evaluate", json=body)


# 25.4 Domain errors -> 4xx ErrorResponse, no result ------------------------ #
@pytest.mark.parametrize(
    ("expression", "angle_mode"),
    [
        ("asin(2)", "radians"),
        ("acos(2)", "radians"),
        ("tan(90)", "degrees"),      # odd multiple of 90 deg -> singularity
        ("sqrt(-1)", "radians"),
        ("root(-8, 2)", "radians"),  # even-degree root of negative
        ("ln(0)", "radians"),
        ("log10(-5)", "radians"),
        ("root(5, 0)", "radians"),   # zero degree
        ("(-8) ^ 0.5", "radians"),   # negative base, non-integer exponent
    ],
)
def test_domain_errors_return_4xx_with_error_and_no_result(
    expression: str, angle_mode: str
) -> None:
    response = _post(expression, angle_mode)
    assert 400 <= response.status_code < 500
    body = response.json()
    assert "error" in body and isinstance(body["error"], str) and body["error"]
    assert "result" not in body


# 17.9 / 24.3 angle mode defaults to radians -------------------------------- #
def test_omitted_angle_mode_behaves_as_radians() -> None:
    # sin(pi/2) == 1 in radians; omitting angle_mode must match explicit radians.
    omitted = _post("sin(pi / 2)")
    explicit = _post("sin(pi / 2)", "radians")
    assert omitted.status_code == 200
    assert explicit.status_code == 200
    assert omitted.json() == explicit.json()


def test_omitted_angle_mode_is_radians_not_degrees() -> None:
    # In radians sin(1) != sin(1 degree); confirm the default is radians.
    omitted = _post("sin(1)").json()["result"]
    radians = _post("sin(1)", "radians").json()["result"]
    assert omitted == radians


# 17.10 / 24.4 invalid angle mode -> 4xx ------------------------------------ #
def test_invalid_angle_mode_rejected() -> None:
    response = _post("sin(1)", "grads")
    assert 400 <= response.status_code < 500
    body = response.json()
    assert "error" in body
    assert "result" not in body


def test_valid_angle_modes_accepted() -> None:
    for mode in ("radians", "degrees"):
        response = _post("cos(0)", mode)
        assert response.status_code == 200
        assert "result" in response.json()
