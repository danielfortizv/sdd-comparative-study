import threading
import copy
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

class ResponseCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves an item from the cache. Returns None if not found or expired.
        """
        with self._lock:
            entry = self._cache.get(key)
            if not entry:
                return None
            # Check expiration (offset-aware comparison)
            if datetime.now(timezone.utc) > entry["expires_at"]:
                del self._cache[key]
                return None
            return entry["content"]

    def set(self, key: str, content: Any, ttl_seconds: int = 60) -> datetime:
        """
        Sets an item in the cache with a specified TTL.
        Returns the expiration datetime.
        """
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        # Deep copy to prevent mutability issues with shared references (e.g. database list)
        cached_content = copy.deepcopy(content)
        with self._lock:
            self._cache[key] = {
                "content": cached_content,
                "expires_at": expires_at
            }
        return expires_at

    def invalidate(self, key: str) -> None:
        """
        Removes a specific key from the cache.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self) -> None:
        """
        Clears all cached entries.
        """
        with self._lock:
            self._cache.clear()

# Global singleton cache instance
response_cache = ResponseCache()
