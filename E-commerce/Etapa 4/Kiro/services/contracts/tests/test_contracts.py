"""Unit tests for the shared contracts package (Stage 4 R7.1)."""

from __future__ import annotations

from contracts.envelope import EventEnvelope
from contracts.events import REVIEW_APPROVED, ReviewProjectionData
from contracts.tokens import issue_token, verify_token


def test_token_round_trip_preserves_claims():
    token = issue_token("cust-1", "alice", True, secret="s")
    claims = verify_token(token, secret="s")
    assert claims is not None
    assert claims.customer_id == "cust-1"
    assert claims.identifier == "alice"
    assert claims.is_moderator is True


def test_token_rejected_on_tamper():
    token = issue_token("cust-1", "alice", False, secret="s")
    tampered = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    assert verify_token(tampered, secret="s") is None


def test_token_rejected_with_wrong_secret():
    token = issue_token("cust-1", "alice", False, secret="right")
    assert verify_token(token, secret="wrong") is None


def test_token_rejected_when_malformed():
    assert verify_token("not-a-token", secret="s") is None
    assert verify_token("", secret="s") is None


def test_envelope_round_trip():
    data = ReviewProjectionData(
        review_id="r1",
        product_id="p-001",
        author_identity="alice",
        rating=5,
        text="Great",
    ).model_dump(by_alias=True)
    env = EventEnvelope.build(REVIEW_APPROVED, data, correlation_id="corr-1")
    parsed = EventEnvelope.parse(env.to_bytes())
    assert parsed.event_type == REVIEW_APPROVED
    assert parsed.schema_version == "1"
    assert parsed.correlation_id == "corr-1"
    assert parsed.data["reviewId"] == "r1"
    assert parsed.event_id == env.event_id


def test_envelope_parse_rejects_non_json():
    try:
        EventEnvelope.parse(b"not json")
    except ValueError:
        return
    raise AssertionError("expected ValueError for non-JSON payload")
