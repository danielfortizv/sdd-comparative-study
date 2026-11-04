"""Degree/radian conversion round-trip property P15 (task 27.3)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_EVEN, Context

from hypothesis import given

from app.engine.scientific import deg2rad, rad2deg
from tests.properties import strategies as S

_SIG10 = Context(prec=10, rounding=ROUND_HALF_EVEN)


# Feature: web-calculator, Property 15: Degree/radian conversion round-trips via Decimal pi
@S.PROPERTY_SETTINGS
@given(angle=S.atan_operands())
def test_p15_conversion_roundtrip(angle: Decimal) -> None:
    """Validates: Requirements 17.5"""
    # deg -> rad -> deg restores the original angle to >=10 sig digits.
    back = rad2deg(deg2rad(angle))
    assert _SIG10.plus(back) == _SIG10.plus(angle)
    # A single conversion equals the Decimal reference deg * pi / 180.
    expected = angle * S.REFERENCE_PI / Decimal(180)
    assert _SIG10.plus(deg2rad(angle)) == _SIG10.plus(expected)
