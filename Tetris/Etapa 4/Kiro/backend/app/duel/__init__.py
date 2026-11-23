"""In-memory duel subsystem for Tetris Stage 4 Option A (M3).

This package holds the WebSocket duel's server-side state and lifecycle,
kept fully separate from the solo HTTP stores and the solo SQLite leaderboard.
Duel games are PRIVATE per-seat ``engine.new_game`` ``Game`` objects: they are
never registered in ``app/store.py``, never exposed via ``GET /api/games/{id}``,
never written to the solo SQLite, and never added to the solo leaderboard.

Modules:

* ``rooms``   -- ``Seat`` / ``Room`` / ``RoomManager`` data structures and the
                 bounded, injectable-clock room lifecycle (``cleanup_tick``).
* ``gravity`` -- per-board server-side gravity (added by task 13.1).
"""

from __future__ import annotations

__all__ = ["rooms"]
