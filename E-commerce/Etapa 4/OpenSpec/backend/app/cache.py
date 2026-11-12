import time
import threading
from typing import Any, Dict, Optional

class InMemoryCache:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.lock = threading.Lock()
        self.store: Dict[str, Dict[str, Any]] = {}  # key -> {"value": Any, "expires_at": float}

    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key not in self.store:
                return None
            item = self.store[key]
            if time.time() > item["expires_at"]:
                del self.store[key]
                return None
            return item["value"]

    def set(self, key: str, value: Any, ttl_seconds: int = 60):
        with self.lock:
            # Enforce bounding (FIFO)
            if len(self.store) >= self.max_size and key not in self.store:
                # Remove the oldest inserted key
                oldest_key = next(iter(self.store))
                del self.store[oldest_key]
            
            self.store[key] = {
                "value": value,
                "expires_at": time.time() + ttl_seconds
            }

    def invalidate_key(self, key: str):
        with self.lock:
            if key in self.store:
                del self.store[key]

    def invalidate_pattern(self, pattern: str):
        with self.lock:
            keys_to_delete = [k for k in self.store.keys() if pattern in k]
            for k in keys_to_delete:
                del self.store[k]

    def clear(self):
        with self.lock:
            self.store.clear()

# Global cache singleton
cache_instance = InMemoryCache(max_size=100)
