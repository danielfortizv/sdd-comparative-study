"""Domain-error property P17 (task 27.5): every out-of-domain scientific
expression is rejected with a DomainError and never returns a result."""

from __future__ import annotations

import pytest
from hypothesis import given

from app.engine import evaluate_expression
from app.engine.errors import DomainError
from tests.properties import strategies as S


# Feature: web-calculator, Property 17: Domain errors always signal a 4xx and never return a result
@S.PROPERTY_SETTINGS
@given(expression=S.asin_acos_out_of_domain_expressions())
def test_p17_asin_acos_out_of_domain(expression: str) -> None:
    """Validates: Requirements 17.8, 24.8"""
    with pytest.raises(DomainError):
        evaluate_expression(expression, angle_mode="radians")


@S.PROPERTY_SETTINGS
@given(expression=S.sqrt_negative_expressions())
def test_p17_sqrt_negative(expression: str) -> None:
    """Validates: Requirements 18.8, 24.8"""
    with pytest.raises(DomainError):
        evaluate_expression(expression, angle_mode="radians")


@S.PROPERTY_SETTINGS
@given(expression=S.even_root_negative_expressions())
def test_p17_even_root_negative(expression: str) -> None:
    """Validates: Requirements 18.8, 24.8"""
    with pytest.raises(DomainError):
        evaluate_expression(expression, angle_mode="radians")


@S.PROPERTY_SETTINGS
@given(expression=S.zero_degree_root_expressions())
def test_p17_zero_degree_root(expression: str) -> None:
    """Validates: Requirements 18.10, 24.8"""
    with pytest.raises(DomainError):
        evaluate_expression(expression, angle_mode="radians")


@S.PROPERTY_SETTINGS
@given(expression=S.log_non_positive_expressions())
def test_p17_log_non_positive(expression: str) -> None:
    """Validates: Requirements 18.7, 24.8"""
    with pytest.raises(DomainError):
        evaluate_expression(expression, angle_mode="radians")


@S.PROPERTY_SETTINGS
@given(expression=S.negative_base_fractional_exponent_expressions())
def test_p17_negative_base_fractional_exponent(expression: str) -> None:
    """Validates: Requirements 18.9, 24.8"""
    with pytest.raises(DomainError):
        evaluate_expression(expression, angle_mode="radians")


@S.PROPERTY_SETTINGS
@given(expression=S.tan_singularity_expressions())
def test_p17_tan_singularity_in_degrees(expression: str) -> None:
    """Validates: Requirements 17.7, 24.8 (tan singularity is exact in degrees)"""
    with pytest.raises(DomainError):
        evaluate_expression(expression, angle_mode="degrees")
