"""Real multi-process, real-broker acceptance tests (Stage 4 R7.2, R7.3).

These drive the running four-service stack only through the gateway over HTTP and
prove genuine cross-process event propagation via RabbitMQ:

- purchasing journey (commerce);
- a customer submitting a review that is hidden from the public projection while
  pending;
- moderator approval propagating through the broker to the commerce projection
  so the review becomes publicly visible within a bounded window;
- a regular customer denied moderation (403);
- duplicate delivery producing no double effect;
- a consumer outage followed by recovery without losing the accepted change.
"""

from __future__ import annotations

import json
import time

import pika
import pytest

from conftest import restart_commerce


def _login(client, identifier, password):
    resp = client.post(
        "/auth/login", json={"identifier": identifier, "password": password}
    )
    assert resp.status_code == 200, resp.text
    return resp


def _register(client, identifier, password="password123"):
    resp = client.post(
        "/auth/register", json={"identifier": identifier, "password": password}
    )
    assert resp.status_code == 201, resp.text


def _poll_public_review(client, product_id, text, timeout=15.0):
    """Poll the public projection until a review with ``text`` appears."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        resp = client.get(f"/products/{product_id}/reviews")
        last = resp.json()
        if any(r["text"] == text for r in last["reviews"]):
            return last
        time.sleep(0.5)
    return last


def test_purchasing_journey(stack):
    with stack.client() as client:
        products = client.get("/products").json()
        assert len(products) == 6
        resp = client.post(
            "/checkout/confirm",
            json={"items": [{"productId": "p-001", "quantity": 2}]},
        )
        assert resp.status_code == 200
        assert resp.json()["simulated"] is True


def test_review_lifecycle_via_real_broker(stack):
    product = "p-002"
    text = f"Great keyboard {int(time.time())}"
    with stack.client() as client:
        # 1. Customer registers + signs in and submits a review.
        _register(client, "alice")
        _login(client, "alice", "password123")
        submit = client.post(
            f"/products/{product}/reviews", json={"rating": 5, "text": text}
        )
        assert submit.status_code == 201
        assert submit.json()["moderationState"] == "pending"

        # 2. Pending review is NOT in the public projection.
        public = client.get(f"/products/{product}/reviews").json()
        assert all(r["text"] != text for r in public["reviews"])
        # ...but the author sees their own pending review.
        assert public["ownReview"] is not None
        assert public["ownReview"]["moderationState"] == "pending"

        review_id = submit.json()["id"]

        # 3. Moderator signs in and approves.
        _login(client, "moderator", "moderator123")
        queue = client.get("/moderation/reviews").json()
        assert any(r["id"] == review_id for r in queue)
        approve = client.post(f"/moderation/reviews/{review_id}/approve")
        assert approve.status_code == 200

        # 4. Event propagates across processes via the broker -> public.
        client.post("/auth/logout")
        public = _poll_public_review(client, product, text)
        assert any(r["text"] == text for r in public["reviews"]), (
            "approved review did not propagate to the commerce projection"
        )
        assert public["summary"]["count"] >= 1


def test_customer_denied_moderation(stack):
    with stack.client() as client:
        _register(client, "bob")
        _login(client, "bob", "password123")
        queue = client.get("/moderation/reviews")
        assert queue.status_code == 403
        assert queue.json()["error"] == "moderator_required"


def test_duplicate_delivery_is_idempotent(stack):
    """Publish the same approved event twice; the projection count is unchanged."""
    product = "p-003"
    text = f"Dup hub {int(time.time())}"
    with stack.client() as client:
        _register(client, "carol")
        _login(client, "carol", "password123")
        review_id = client.post(
            f"/products/{product}/reviews", json={"rating": 4, "text": text}
        ).json()["id"]
        _login(client, "moderator", "moderator123")
        client.post(f"/moderation/reviews/{review_id}/approve")
        client.post("/auth/logout")

        # Wait for the genuine approval to land.
        public = _poll_public_review(client, product, text)
        assert any(r["text"] == text for r in public["reviews"])
        count_after_approve = client.get(f"/products/{product}/reviews").json()[
            "summary"
        ]["count"]

        # Re-publish the SAME event id directly to the broker (duplicate).
        event = {
            "eventId": f"dup-{review_id}",
            "eventType": f"{stack.namespace}.review.approved",
            "schemaVersion": "1",
            "occurredAt": "2026-01-01T00:00:00Z",
            "correlationId": "dup-corr",
            "data": {
                "reviewId": review_id,
                "productId": product,
                "authorIdentity": "carol",
                "rating": 4,
                "title": None,
                "text": text,
                "images": [],
                "moderationState": "approved",
            },
        }
        _publish(stack, event)
        _publish(stack, event)  # exact duplicate eventId

        # Give the consumer time to process both; count must not increase.
        time.sleep(3)
        count_after_dup = client.get(f"/products/{product}/reviews").json()[
            "summary"
        ]["count"]
        assert count_after_dup == count_after_approve


def test_broker_consumer_outage_then_recovery(stack):
    """Approve while the consumer is down; the change is not lost after restart."""
    product = "p-004"
    text = f"Resilient mouse {int(time.time())}"
    with stack.client() as client:
        _register(client, "dave")
        _login(client, "dave", "password123")
        review_id = client.post(
            f"/products/{product}/reviews", json={"rating": 5, "text": text}
        ).json()["id"]

        # Take the commerce consumer DOWN before approving.
        stack.procs["commerce"].terminate()
        stack.procs["commerce"].wait(timeout=10)

        # Approve while the consumer is offline. The reviews service commits the
        # decision + outbox row locally and publishes to the durable queue; the
        # event waits for the consumer to come back.
        _login(client, "moderator", "moderator123")
        approve = client.post(f"/moderation/reviews/{review_id}/approve")
        assert approve.status_code == 200
        client.post("/auth/logout")

        # Bring the consumer back; the durable message is delivered and applied.
        restart_commerce(stack)
        public = _poll_public_review(client, product, text, timeout=20.0)
        assert any(r["text"] == text for r in public["reviews"]), (
            "accepted change was lost across the consumer outage"
        )


def _publish(stack, event: dict) -> None:
    params = pika.URLParameters(stack.env["AMQP_URL"])
    conn = pika.BlockingConnection(params)
    try:
        channel = conn.channel()
        exchange = f"{stack.namespace}.events"
        channel.exchange_declare(exchange=exchange, exchange_type="topic", durable=True)
        channel.confirm_delivery()
        channel.basic_publish(
            exchange=exchange,
            routing_key=event["eventType"],
            body=json.dumps(event).encode("utf-8"),
            properties=pika.BasicProperties(delivery_mode=2),
            mandatory=True,
        )
    finally:
        conn.close()
