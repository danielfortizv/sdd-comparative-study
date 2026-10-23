"""Angle-mode property P22 (task 27.8): omitted angle mode defaults to radians;
any value other than radians/degrees is rejected with a 4xx and no result."""

from __future__ import annotations

from hypothesis import given
import hypothesis.strategies as st
from fastapi.testclient import TestClient

from app.main import app
from tests.properties import strategies as S

client = TestClient(app)


# Feature: web-calculator, Property 22: Angle mode defaults to radians and rejects invalid values
@S.PROPERTY_SETTINGS
@given(value=S.trig_operands())
def test_p22_omitted_angle_mode_defaults_to_radians(value) -> None:
    """Validates: Requirements 17.9, 24.3"""
    expression = f"sin({value})"
    omitted = client.post("/api/v1/evaluate", json={"expression": expression})
    radians = client.post(
        "/api/v1/evaluate", json={"expression": expression, "angle_mode": "radians"}
    )
    assert omitted.status_code == 200
    assert radians.status_code == 200
    assert omitted.json() == radians.json()


@S.PROPERTY_SETTINGS
@given(
    mode=st.text(min_size=1, max_size=12).filter(
        lambda s: s not in ("radians", "degrees")
    )
)
def test_p22_invalid_angle_mode_rejected(mode: str) -> None:
    """Validates: Requirements 17.10, 24.4"""
    response = client.post(
        "/api/v1/evaluate",
        json={"expression": "sin(1)", "angle_mode": mode},
    )
    assert 400 <= response.status_code < 500
    assert "result" not in response.json()
