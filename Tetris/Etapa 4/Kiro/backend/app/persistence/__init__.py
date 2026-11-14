"""High-score persistence package (Stage 3, Option A).

Holds the SQLite-backed high-score store. Kept separate from the in-memory
game repository (``app/store.py``) so persistence concerns do not leak into the
authoritative in-memory game state.
"""
