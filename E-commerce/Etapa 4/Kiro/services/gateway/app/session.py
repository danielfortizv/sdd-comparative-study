"""Browser-session <-> service-token binding held by the gateway (R2.3).

The Stage 1-3 frontend sends no token or credential of its own; the monolith
used a single in-process session. The gateway preserves that UX by holding the
binding between an httpOnly session cookie it issues and the signed service
token returned by identity on login. The token (which carries the role) is
never exposed to the browser, and no client-supplied role header is ever
trusted.
"""

from __future__ import annotations

import threading
import uuid


class SessionBindingStore:
    """In-memory cookie-id -> service-token map for the gateway process."""

    def __init__(self) -> None:
        self._by_cookie: dict[str, str] = {}
        self._lock = threading.Lock()

    def create(self, token: str) -> str:
        """Bind a new cookie id to ``token`` and return the cookie id."""
        cookie_id = uuid.uuid4().hex
        with self._lock:
            self._by_cookie[cookie_id] = token
        return cookie_id

    def token_for(self, cookie_id: str | None) -> str | None:
        if not cookie_id:
            return None
        with self._lock:
            return self._by_cookie.get(cookie_id)

    def drop(self, cookie_id: str | None) -> None:
        if not cookie_id:
            return
        with self._lock:
            self._by_cookie.pop(cookie_id, None)

    def clear(self) -> None:
        with self._lock:
            self._by_cookie.clear()
