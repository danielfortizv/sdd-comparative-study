import time
import copy

class ResponseCache:
    def __init__(self, ttl_seconds: float = 60.0):
        self.ttl = ttl_seconds
        # Structure: { key: {"data": value, "expires_at": float} }
        self._cache = {}

    def get(self, key: str):
        now = time.time()
        entry = self._cache.get(key)
        if entry:
            if now < entry["expires_at"]:
                return copy.deepcopy(entry["data"])
            else:
                # Expired
                del self._cache[key]
        return None

    def set(self, key: str, value):
        self._cache[key] = {
            "data": copy.deepcopy(value),
            "expires_at": time.time() + self.ttl
        }

    def invalidate(self, key: str):
        if key in self._cache:
            del self._cache[key]

    def clear_all(self):
        self._cache.clear()

# Global cache instance
response_cache = ResponseCache(ttl_seconds=60.0)
