"""Shared, stateless contracts for the Stage 4 microservices.

This package carries only schema and utility code (event envelopes, event type
constants and payload models, signed-token helpers, and environment-based
settings). It holds no runtime business state, so importing it does not couple
services together (Stage 4 requirement 1.4). Each service installs it editable
into its own virtual environment.
"""

from contracts.envelope import EventEnvelope
from contracts.events import (
    REVIEW_APPROVED,
    REVIEW_REJECTED,
    ReviewProjectionData,
    ReviewRejectedData,
)
from contracts.settings import Settings, get_settings
from contracts.tokens import TokenClaims, issue_token, verify_token

__all__ = [
    "EventEnvelope",
    "REVIEW_APPROVED",
    "REVIEW_REJECTED",
    "ReviewProjectionData",
    "ReviewRejectedData",
    "Settings",
    "get_settings",
    "TokenClaims",
    "issue_token",
    "verify_token",
]
