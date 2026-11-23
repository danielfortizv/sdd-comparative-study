"""Live RabbitMQ consumer that keeps the public projection coherent (R3, R4).

Runs in a background daemon thread started with the commerce service. It:

- declares the durable topology (exchange, queue, DLX, DLQ);
- consumes with ``prefetch=1`` and **manual acknowledgement**;
- is **idempotent** via the ``processed_events`` table (duplicate deliveries
  produce no additional effect, R4.2);
- applies **bounded retry** per delivery and routes a poison message to the
  dead-letter queue by rejecting without requeue after the bound (R4.5);
- **reconnects with exponential backoff** on a broker outage (R4.5).

At-least-once delivery with an idempotent consumer; exactly-once is NOT claimed.
"""

from __future__ import annotations

import logging
import threading
import time

import pika

from contracts.envelope import EventEnvelope
from contracts.settings import get_settings

from app import broker
from app.db import ProjectionStore
from app.projection import UnknownEventError, apply_event

logger = logging.getLogger("commerce.consumer")

MAX_ATTEMPTS = 5
_BASE_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0


class ProjectionConsumer:
    """Background consumer for review-moderation events."""

    def __init__(self, store: ProjectionStore, amqp_url: str | None = None) -> None:
        self._store = store
        self._amqp_url = amqp_url or get_settings().amqp_url
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        # Per-delivery retry counters keyed by event id (bounded retry, R4.5).
        self._attempts: dict[str, int] = {}

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="projection-consumer", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5)
        self._thread = None

    def _run(self) -> None:
        backoff = _BASE_BACKOFF_SECONDS
        while not self._stop.is_set():
            try:
                self._consume_forever()
                backoff = _BASE_BACKOFF_SECONDS
            except Exception as error:  # noqa: BLE001 - resilience boundary
                if self._stop.is_set():
                    break
                logger.warning("Consumer connection lost (%s); retrying", error)
                time.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)

    def _consume_forever(self) -> None:
        params = pika.URLParameters(self._amqp_url)
        connection = pika.BlockingConnection(params)
        try:
            channel = connection.channel()
            broker.declare_topology(channel)
            channel.basic_qos(prefetch_count=1)

            for method, _props, body in channel.consume(
                broker.COMMERCE_QUEUE, inactivity_timeout=1.0
            ):
                if self._stop.is_set():
                    break
                if method is None:
                    continue  # idle tick; lets us observe the stop flag
                self._handle(channel, method, body)
        finally:
            try:
                connection.close()
            except Exception:  # noqa: BLE001
                pass

    def _handle(self, channel, method, body: bytes) -> None:
        try:
            envelope = EventEnvelope.parse(body)
        except ValueError:
            # Unparseable: dead-letter immediately (poison).
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        try:
            apply_event(envelope, self._store)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            self._attempts.pop(envelope.event_id, None)
        except UnknownEventError:
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            self._attempts.pop(envelope.event_id, None)
        except Exception as error:  # noqa: BLE001 - transient processing failure
            attempts = self._attempts.get(envelope.event_id, 0) + 1
            self._attempts[envelope.event_id] = attempts
            if attempts >= MAX_ATTEMPTS:
                logger.error(
                    "Dead-lettering event %s after %d attempts: %s",
                    envelope.event_id,
                    attempts,
                    error,
                )
                channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                self._attempts.pop(envelope.event_id, None)
            else:
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
