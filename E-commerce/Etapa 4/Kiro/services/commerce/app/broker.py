"""RabbitMQ topology declaration shared by publisher and consumer (Stage 4 R4).

Centralizes the durable exchange, queue, dead-letter exchange, and dead-letter
queue names and their declaration so the reviews publisher and the commerce
consumer agree on the same topology.
"""

from __future__ import annotations

import pika

from contracts.settings import get_settings

_NS = get_settings().event_namespace

EXCHANGE = f"{_NS}.events"
DLX = f"{_NS}.events.dlx"
COMMERCE_QUEUE = f"{_NS}.commerce.projection"
COMMERCE_DLQ = f"{_NS}.commerce.projection.dlq"
# Bind both moderation routing keys.
ROUTING_KEYS = (f"{_NS}.review.approved", f"{_NS}.review.rejected")


def declare_topology(channel: "pika.adapters.blocking_connection.BlockingChannel") -> None:
    """Declare the durable exchange, DLX, consumer queue, DLQ and bindings.

    Idempotent: declaring already-existing entities with the same arguments is
    a no-op on the broker. Called by both the publisher (exchange only is
    strictly needed) and the consumer (full topology).
    """
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
    channel.exchange_declare(exchange=DLX, exchange_type="topic", durable=True)

    channel.queue_declare(
        queue=COMMERCE_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": DLX,
            "x-dead-letter-routing-key": COMMERCE_DLQ,
        },
    )
    for routing_key in ROUTING_KEYS:
        channel.queue_bind(
            queue=COMMERCE_QUEUE, exchange=EXCHANGE, routing_key=routing_key
        )

    channel.queue_declare(queue=COMMERCE_DLQ, durable=True)
    channel.queue_bind(queue=COMMERCE_DLQ, exchange=DLX, routing_key=COMMERCE_DLQ)


def declare_exchange_only(
    channel: "pika.adapters.blocking_connection.BlockingChannel",
) -> None:
    """Declare just the durable events exchange (publisher side)."""
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
