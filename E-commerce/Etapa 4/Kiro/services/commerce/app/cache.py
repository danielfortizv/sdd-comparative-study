"""Bounded, TTL-based response cache for public catalog reads (Stage 3 parity).

Ported from the Stage 3 monolith's ``response_cache`` so the commerce service
preserves the same bounded-cache behavior and the moderation-driven
invalidation hook. An event-driven projection change invalidates the cache so
the next public read is coherent (Stage 4 R3.5).
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Callable


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


DEFAULT_TTL_SECONDS = _int_env("CATALOG_CACHE_TTL_SECONDS", 30)
DEFAULT_MAX_ENTRIES = _int_env("CATALOG_CACHE_MAX_ENTRIES", 256)


@dataclass
class CacheEntry:
    body: bytes
    media_type: str
    expires_at: float


class BoundedTTLCache:
    def __init__(self, ttl_seconds: int, max_entries: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._max_entries = max(1, max_entries)
        self._entries: "OrderedDict[str, CacheEntry]" = OrderedDict()
        self._lock = threading.Lock()

    @property
    def enabled(self) -> bool:
        return self._ttl_seconds > 0

    @property
    def ttl_seconds(self) -> int:
        return self._ttl_seconds

    def get(self, key: str) -> CacheEntry | None:
        if not self.enabled:
            return None
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry

    def set(self, key: str, body: bytes, media_type: str) -> None:
        if not self.enabled:
            return
        expires_at = time.monotonic() + self._ttl_seconds
        with self._lock:
            self._entries[key] = CacheEntry(body, media_type, expires_at)
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_entries:
                self._entries.popitem(last=False)

    def invalidate(self, predicate: Callable[[str], bool] | None = None) -> int:
        with self._lock:
            if predicate is None:
                removed = len(self._entries)
                self._entries.clear()
                return removed
            keys = [k for k in self._entries if predicate(k)]
            for key in keys:
                del self._entries[key]
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


response_cache = BoundedTTLCache(DEFAULT_TTL_SECONDS, DEFAULT_MAX_ENTRIES)


def invalidate() -> int:
    """Invalidate the whole catalog/review cache (projection-change hook)."""
    return response_cache.invalidate()
