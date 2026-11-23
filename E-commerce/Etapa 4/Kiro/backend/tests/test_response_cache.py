"""Unit tests for the bounded TTL response cache (Stage 3, Task 4).

Covers the two boundedness properties the cache guarantees:

- **TTL expiry** (Requirement 5.3): an entry is a miss once its TTL elapses.
- **Max-entry eviction** (Requirement 5.2): the cache never exceeds its entry
  bound; the oldest-inserted entry is evicted first.
- **Invalidation** (Requirement 5.5): the invalidation hook drops entries.
"""

from __future__ import annotations

import time

from app.services.response_cache import BoundedTTLCache


def test_get_returns_stored_entry_before_expiry() -> None:
    cache = BoundedTTLCache(ttl_seconds=30, max_entries=8)
    cache.set("GET /products", b"[]", "application/json")

    entry = cache.get("GET /products")
    assert entry is not None
    assert entry.body == b"[]"
    assert entry.media_type == "application/json"


def test_entry_expires_after_ttl() -> None:
    # A tiny TTL makes the expiry observable without a long sleep. The cache
    # uses a monotonic clock, so sleeping just past the TTL is sufficient.
    cache = BoundedTTLCache(ttl_seconds=1, max_entries=8)
    cache.set("GET /products", b"[]", "application/json")
    assert cache.get("GET /products") is not None

    time.sleep(1.1)
    assert cache.get("GET /products") is None


def test_eviction_keeps_cache_within_max_entries() -> None:
    cache = BoundedTTLCache(ttl_seconds=30, max_entries=3)
    for index in range(5):
        cache.set(f"GET /products/p-{index}", b"{}", "application/json")

    # Only the three most-recently-inserted keys survive.
    assert cache.get("GET /products/p-0") is None
    assert cache.get("GET /products/p-1") is None
    assert cache.get("GET /products/p-2") is not None
    assert cache.get("GET /products/p-3") is not None
    assert cache.get("GET /products/p-4") is not None


def test_ttl_zero_disables_caching() -> None:
    cache = BoundedTTLCache(ttl_seconds=0, max_entries=8)
    assert cache.enabled is False
    cache.set("GET /products", b"[]", "application/json")
    assert cache.get("GET /products") is None


def test_invalidate_drops_all_entries() -> None:
    cache = BoundedTTLCache(ttl_seconds=30, max_entries=8)
    cache.set("GET /products", b"[]", "application/json")
    cache.set("GET /products/p-1", b"{}", "application/json")

    removed = cache.invalidate()
    assert removed == 2
    assert cache.get("GET /products") is None
    assert cache.get("GET /products/p-1") is None


def test_invalidate_with_predicate_drops_matching_entries_only() -> None:
    cache = BoundedTTLCache(ttl_seconds=30, max_entries=8)
    cache.set("GET /products", b"[]", "application/json")
    cache.set("GET /products/p-1", b"{}", "application/json")

    removed = cache.invalidate(lambda key: key.endswith("p-1"))
    assert removed == 1
    assert cache.get("GET /products") is not None
    assert cache.get("GET /products/p-1") is None
