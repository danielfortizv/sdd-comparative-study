"""WebSocket duel package (Stage 4 Option A).

Houses the versioned duel wire contract (``contract.py``) and, in later M3
tasks, the ``/ws/duel`` endpoint, room manager, and server-side gravity. This
package is intentionally isolated from the solo HTTP stack: the duel runs on
PRIVATE engine ``Game`` objects and performs zero SQLite writes.
"""
