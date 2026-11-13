"""Shared API error constants (Stage 3, Option A).

The controlled storage-failure message is a single generic, human-readable
English string. It indicates a storage failure WITHOUT exposing any filesystem
path, SQL text, exception/class name, or stack trace, so a 503 response never
leaks internals (Requirement 7.4, 7.5).
"""

from __future__ import annotations

STORAGE_UNAVAILABLE_MESSAGE = (
    "High-score storage is temporarily unavailable. Please try again later."
)
