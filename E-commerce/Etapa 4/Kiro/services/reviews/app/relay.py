"""Transactional-outbox relay publisher (Stage 4 R4.1, R4.3, R4.4).

Runs in a background daemon thread. On each tick it reads unsent outbox rows and
publishes them to the durable events exchange on a **publisher-confirm** channel;
a row is marked sent only after the broker confirms the message. If the broker
is unreachable the rows stay unsent and are retried on a later tick, so an
accepted moderation decision is never lost across a broker outage. The relay
reconnects with exponential backoff.

The topology (durable exchange) matches the commerce consumer's declaration.
"""

from __future__ import annotations

import logging
import threading
import time

import pika

from contracts.settings import get_settings

from app.db import ReviewStore

logger = logging.getLogger("reviews.relay")

_NS = get_settings().event_namespace
EXCHANGE = f"{_NS}.events"

_POLL_SECONDS = 0.5
_BASE_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 30.0


class OutboxRelay:
    def __init__(self, store: ReviewStore, amqp_url: str | None = None) -> None:
        self._store = store
        self._amqp_url = amqp_url or get_settings().amqp_url
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="outbox-relay", daemon=True
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
            connection = None
            try:
                connection = pika.BlockingConnection(
                    pika.URLParameters(self._amqp_url)
                )
                channel = connection.channel()
                channel.exchange_declare(
                    exchange=EXCHANGE, exchange_type="topic", durable=True
                )
                channel.confirm_delivery()  # publisher confirms
                backoff = _BASE_BACKOFF_SECONDS

                while not self._stop.is_set():
                    published_any = self._drain_once(channel)
                    # Short sleep when idle; keep tight when there is a backlog.
                    if not published_any:
                        time.sleep(_POLL_SECONDS)
            except Exception as error:  # noqa: BLE001 - resilience boundary
                if self._stop.is_set():
                    break
                logger.warning("Relay broker connection failed (%s); retrying", error)
                time.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_SECONDS)
            finally:
                if connection is not None:
                    try:
                        connection.close()
                    except Exception:  # noqa: BLE001
                        pass

    def _drain_once(self, channel) -> bool:
        rows = self._store.unsent_outbox()
        if not rows:
            return False
        for row in rows:
            if self._stop.is_set():
                break
            try:
                channel.basic_publish(
                    exchange=EXCHANGE,
                    routing_key=row.event_type,
                    body=row.payload.encode("utf-8"),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # persistent
                        content_type="application/json",
                        message_id=row.event_id,
                    ),
                    mandatory=True,
                )
                # confirm_delivery() raises if unconfirmed/nacked, so reaching
                # here means the broker confirmed the persistent message.
                self._store.mark_sent(row.id)
            except Exception as error:  # noqa: BLE001
                self._store.increment_attempts(row.id)
                logger.warning("Failed to publish outbox row %s: %s", row.id, error)
                raise  # bubble up to reconnect; the row stays unsent
        return True
