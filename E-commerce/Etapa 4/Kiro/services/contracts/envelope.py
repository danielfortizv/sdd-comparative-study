"""Versioned JSON event envelope shared by publisher and consumer (R A7).

Every business event is wrapped in this envelope so it carries a stable event
identity (for idempotent consumption), a correlation identity (for tracing a
flow across services), a namespaced type, a schema version, a timestamp, and a
typed payload. The envelope serializes to compact JSON bytes for the broker and
parses back defensively.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

SCHEMA_VERSION = "1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class EventEnvelope(BaseModel):
    """A versioned event envelope (camelCase on the wire)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    schema_version: str = SCHEMA_VERSION
    occurred_at: str = Field(default_factory=_now_iso)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    data: dict[str, Any]

    @classmethod
    def build(
        cls,
        event_type: str,
        data: dict[str, Any],
        *,
        correlation_id: str | None = None,
        event_id: str | None = None,
    ) -> "EventEnvelope":
        """Construct an envelope for ``event_type`` carrying ``data``."""
        kwargs: dict[str, Any] = {"event_type": event_type, "data": data}
        if correlation_id is not None:
            kwargs["correlation_id"] = correlation_id
        if event_id is not None:
            kwargs["event_id"] = event_id
        return cls(**kwargs)

    def to_bytes(self) -> bytes:
        """Serialize to compact JSON bytes for publishing."""
        return self.model_dump_json(by_alias=True).encode("utf-8")

    @classmethod
    def parse(cls, raw: bytes | str) -> "EventEnvelope":
        """Parse envelope bytes/str from the broker.

        Raises:
            ValueError: If the payload is not a valid envelope.
        """
        try:
            payload = json.loads(raw)
        except (ValueError, TypeError) as error:
            raise ValueError("Event payload is not valid JSON.") from error
        return cls.model_validate(payload)
