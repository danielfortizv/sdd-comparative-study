"""Bounded, TTL-expiring in-process response cache (service layer, Stage 3).

This module provides a small, self-contained cache used by the catalog cache
middleware to avoid recomputing the session-independent public catalog reads
(``GET /products`` and ``GET /products/{id}``). It is deliberately minimal and
local: no external cache server, no persistence, no paid service.

Safety properties (Stage 3 Requirements 5.2, 5.3, 5.5; Assumptions A3, A4):

- **Bounded size.** The cache holds at most ``max_entries`` entries. When full,
  the oldest-inserted entry is evicted (insertion-ordered eviction), so memory
  is bounded regardless of traffic.
- **Bounded staleness.** Each entry carries an absolute expiry timestamp; a
  ``get`` past expiry is a miss and the stale entry is dropped. No entry can be
  served indefinitely.
- **User-independence.** Only session-independent responses are ever stored (the
  middleware enforces this), so a single shared entry is correct for every
  caller and cannot leak one user's data to another.
- **Explicit invalidation.** ``invalidate`` clears entries (optionally by
  predicate) so a state change elsewhere (e.g. a moderation decision) can force
  freshness even though the catalog itself is unaffected by that change.

The cache is guarded by a ``threading.Lock`` so it is safe under the default
Uvicorn worker. Configuration comes from the environment with safe defaults.
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable


def _env_int(name: str, default: int) -> int:
    """Read a non-negative integer env var, falling back to ``default``."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return value if value >= 0 else default


# Configuration (Assumption A4). TTL of 0 disables caching entirely; the
# middleware then behaves as a pass-through that still marks sensitive routes
# ``no-store``.
DEFAULT_TTL_SECONDS = _env_int("CATALOG_CACHE_TTL_SECONDS", 30)
DEFAULT_MAX_ENTRIES = _env_int("CATALOG_CACHE_MAX_ENTRIES", 256)


@dataclass
class CacheEntry:
    """A stored response body with its media type and absolute expiry time."""

    body: bytes
    media_type: str
    expires_at: float


class BoundedTTLCache:
    """An in-process cache bounded by entry count and per-entry TTL."""

    def __init__(self, *, ttl_seconds: int, max_entries: int) -> None:
        self._ttl_seconds = max(0, ttl_seconds)
        self._max_entries = max(1, max_entries)
        self._lock = threading.Lock()
        self._entries: "OrderedDict[str, CacheEntry]" = OrderedDict()

    @property
    def ttl_seconds(self) -> int:
        """The per-entry time-to-live in seconds (0 means caching disabled)."""
        return self._ttl_seconds

    @property
    def enabled(self) -> bool:
        """Whether caching is active (a positive TTL)."""
        return self._ttl_seconds > 0

    def get(self, key: str) -> CacheEntry | None:
        """Return a live entry for ``key`` or ``None`` (miss or expired)."""
        if not self.enabled:
            return None
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= now:
                # Expired: drop it and report a miss so it is never reused.
                del self._entries[key]
                return None
            # Mark as recently used for insertion-ordered freshness.
            self._entries.move_to_end(key)
            return entry

    def set(self, key: str, body: bytes, media_type: str) -> None:
        """Store a response body for ``key`` with the configured TTL."""
        if not self.enabled:
            return
        expires_at = time.monotonic() + self._ttl_seconds
        with self._lock:
            self._entries[key] = CacheEntry(
                body=body, media_type=media_type, expires_at=expires_at
            )
            self._entries.move_to_end(key)
            # Evict oldest entries until within the bound.
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def invalidate(self, predicate: Callable[[str], bool] | None = None) -> int:
        """Drop all entries, or only those whose key matches ``predicate``.

        Returns the number of entries removed. Called on moderation state
        changes so freshness is enforced even if review responses were cached
        in a future extension (Requirement 5.5).
        """
        with self._lock:
            if predicate is None:
                removed = len(self._entries)
                self._entries.clear()
                return removed
            keys = [key for key in self._entries if predicate(key)]
            for key in keys:
                del self._entries[key]
            return len(keys)

    def clear(self) -> None:
        """Remove all entries. Provided so tests start from a known state."""
        with self._lock:
            self._entries.clear()


# Module-level singleton used by the middleware and the invalidation hook.
response_cache = BoundedTTLCache(
    ttl_seconds=DEFAULT_TTL_SECONDS,
    max_entries=DEFAULT_MAX_ENTRIES,
)


def invalidate() -> int:
    """Invalidate the whole shared cache (moderation-change hook, R5.5)."""
    return response_cache.invalidate()
