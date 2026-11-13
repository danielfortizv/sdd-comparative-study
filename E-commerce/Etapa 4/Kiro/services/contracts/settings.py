"""Environment-based settings shared across the Stage 4 services.

Defaults mirror ``stage4-runtime.json`` so the stack runs out of the box with
the tool-isolated ports and broker vhost, while every value can be overridden
by an environment variable (Stage 4 requirements 6.2, A8). These are deployment
parameters, not functional requirements.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value is not None and value != "" else default


@dataclass(frozen=True)
class Settings:
    """Resolved runtime settings for a Stage 4 process."""

    gateway_port: int
    identity_port: int
    commerce_port: int
    reviews_port: int
    frontend_port: int
    amqp_url: str
    event_namespace: str
    identity_url: str
    commerce_url: str
    reviews_url: str
    token_secret: str
    cache_ttl_seconds: int
    cache_max_entries: int


def get_settings() -> Settings:
    """Build a :class:`Settings` from the environment with runtime defaults."""
    identity_port = int(_env("IDENTITY_PORT", "18201"))
    commerce_port = int(_env("COMMERCE_PORT", "18202"))
    reviews_port = int(_env("REVIEWS_PORT", "18203"))
    return Settings(
        gateway_port=int(_env("GATEWAY_PORT", "18200")),
        identity_port=identity_port,
        commerce_port=commerce_port,
        reviews_port=reviews_port,
        frontend_port=int(_env("FRONTEND_PORT", "18300")),
        amqp_url=_env(
            "AMQP_URL",
            "amqp://ecommerce:stage4-demo@127.0.0.1:5672/stage4_kiro",
        ),
        event_namespace=_env("EVENT_NAMESPACE", "stage4.kiro"),
        identity_url=_env("IDENTITY_URL", f"http://127.0.0.1:{identity_port}"),
        commerce_url=_env("COMMERCE_URL", f"http://127.0.0.1:{commerce_port}"),
        reviews_url=_env("REVIEWS_URL", f"http://127.0.0.1:{reviews_port}"),
        # Local demonstration signing secret only; override in any real use.
        token_secret=_env("STAGE4_TOKEN_SECRET", "stage4-kiro-demo-signing-secret"),
        cache_ttl_seconds=int(_env("CATALOG_CACHE_TTL_SECONDS", "30")),
        cache_max_entries=int(_env("CATALOG_CACHE_MAX_ENTRIES", "256")),
    )
