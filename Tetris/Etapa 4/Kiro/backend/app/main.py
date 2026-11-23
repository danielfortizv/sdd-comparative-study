"""FastAPI application entry point (Stage 3, Option A; Stage 4 M3 duel wiring).

Wires the game and leaderboard routers, initializes the High_Score_Store on
startup via the lifespan handler, and applies a restrictive, configurable CORS
policy. All solo game state is in memory (single worker); only completed-game
high-score summaries are persisted. No authentication, no player names.

Stage 4 M3 adds the duel WebSocket endpoint ``/ws/duel`` on top of the
inherited solo surface WITHOUT changing any solo behavior. The duel's
in-memory ``RoomManager`` and its periodic asyncio tasks (the ``cleanup_tick``
retention sweep and the per-board gravity loop) are owned by the FastAPI
lifespan: they are constructed INSIDE the lifespan and cancelled + released on
shutdown, so repeated ``TestClient`` contexts / event loops never inherit a
stale manager, lock, task, or socket. The duel uses PRIVATE per-seat engine
games and performs ZERO SQL writes; the solo CORS policy and every solo route
are preserved exactly as inherited.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from .api import deps
from .api.games import router as games_router
from .api.high_scores import router as high_scores_router
from .duel.gravity import OutcomeData, run_gravity_loop
from .duel.rooms import CLEANUP_CADENCE, Room, RoomManager
from .persistence.store import HighScoreStore
from .ws import contract
from .ws.duel import (
    DuelEndpoint,
    broadcast_outcome,
    broadcast_room_state,
    resolve_ws_allowed_origins,
)

# Default allowed origins for local development (Vite dev server).
_DEFAULT_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"


class CORSConfigurationError(ValueError):
    """Raised when the configured CORS allow-list is invalid for credentials.

    Credentials are always enabled, so a wildcard origin (``*``) — on its own
    or mixed into a list of concrete origins — is an invalid, insecure
    configuration. Resolving it raises this error at startup (fail closed)
    instead of handing ``*`` to the CORS middleware, which would otherwise
    reflect an arbitrary ``Origin`` with ``Access-Control-Allow-Credentials:
    true`` and grant a credentialed response to any site.
    """


def _resolve_allowed_origins() -> list[str]:
    """Resolve the configurable, restrictive CORS allow-list.

    Reads ``TETRIS_ALLOWED_ORIGINS`` (comma-separated); an unset or empty value
    falls back to the restrictive local-dev origins. Because credentials are
    enabled, a resolved list that contains a literal ``*`` — including a mixed
    list such as ``"https://app.example,*"`` — is rejected with
    :class:`CORSConfigurationError` (fail closed) rather than returned. Only
    concrete explicit origins are ever returned, so a credentialed response can
    never be granted to an arbitrary origin (Req 10.3-10.7).
    """

    raw = os.environ.get("TETRIS_ALLOWED_ORIGINS")
    if raw is None or raw.strip() == "":
        raw = _DEFAULT_ALLOWED_ORIGINS
    origins = [origin.strip() for origin in raw.split(",") if origin.strip()]
    if any(origin == "*" for origin in origins):
        raise CORSConfigurationError(
            "A wildcard '*' origin cannot be combined with credentialed CORS. "
            "Set TETRIS_ALLOWED_ORIGINS to an explicit list of concrete origins."
        )
    return origins


# ---------------------------------------------------------------------------
# Duel runtime holder (Stage 4 M3). The duel's manager, endpoint, and periodic
# tasks are LIFESPAN-OWNED: constructed inside the lifespan and released on
# shutdown. The ``/ws/duel`` route is a thin shim that resolves the CURRENT
# lifespan-owned endpoint at call time, so no manager/lock/task is created at
# import time and nothing leaks across repeated TestClient contexts/event loops.
# ---------------------------------------------------------------------------


class _DuelRuntime:
    """Holds the single lifespan-owned duel manager, endpoint, and tasks.

    A fresh instance is installed by the lifespan on startup and torn down on
    shutdown. The endpoint is resolved per connection via :meth:`endpoint`; a
    connection that arrives while no runtime is active (outside the lifespan) is
    rejected with a policy close rather than touching a stale manager.
    """

    def __init__(self) -> None:
        self.manager: Optional[RoomManager] = None
        self.endpoint: Optional[DuelEndpoint] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._gravity_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Construct the manager + endpoint and launch the periodic tasks.

        Binds the WS Origin allow-list to the proxy host/port (resolved via
        ``resolve_ws_allowed_origins`` — the ``*:5517`` defaults, fail-closed).
        Starts the ``cleanup_tick`` retention sweep and the gravity loop as
        asyncio tasks owned here so shutdown can cancel both cleanly.
        """

        manager = RoomManager()
        self.manager = manager
        self.endpoint = DuelEndpoint(manager, allowed_origins=resolve_ws_allowed_origins())
        self._cleanup_task = asyncio.create_task(_cleanup_loop(manager))
        # Wire the gravity loop's publish hooks (native-14 task 30.2): after the
        # server no-input gravity advances a room's boards, broadcast BOTH
        # authoritative boards to BOTH peers; on a terminal/forfeit resolution,
        # emit the ``outcome`` frame to BOTH peers. Both callbacks only enqueue
        # onto each connected seat's bounded outbound queue (the independent
        # per-connection writer performs the bounded send outside any lock), so
        # a slow peer never blocks the gravity loop or the other peer.
        self._gravity_task = asyncio.create_task(
            run_gravity_loop(
                manager,
                on_state=_publish_room_state,
                on_outcome=_publish_room_outcome,
            )
        )

    async def stop(self) -> None:
        """Cancel the periodic tasks and release all rooms/sockets (no leak).

        Cancels the cleanup + gravity tasks and awaits their cooperative exit,
        then calls ``manager.shutdown`` to drop every room entry AND actively
        tears down each released room (native-19 F3): every room's blocked
        reader/writer are woken and its socket is closed 1001 ``server_shutdown``
        through the single ordered writer seam, and any owned room task is
        released/awaited, so no room, task, or socket is leaked across shutdown.
        A shutdown is a lifecycle abort -- it fabricates NO gameplay winner.
        Idempotent and safe even if ``start`` partially ran.
        """

        for task in (self._cleanup_task, self._gravity_task):
            if task is not None:
                task.cancel()
        for task in (self._cleanup_task, self._gravity_task):
            if task is not None:
                # Await the cancelled task via ``asyncio.wait`` so its
                # cancellation actually COMPLETES before shutdown returns, while
                # a CancelledError aimed at the cancelled task is not swallowed
                # into THIS coroutine (native-14 lifecycle fix for the S7497
                # cancellation-propagation finding). A genuine CancelledError
                # targeting the shutdown coroutine itself still propagates from
                # the surrounding lifespan.
                await asyncio.wait({task})
        if self.manager is not None:
            # Release every room entry AND actually close its sockets / wake its
            # blocked reader+writer / release its owned task (native-19 F3). The
            # periodic cleanup loop is already cancelled above, so shutdown owns
            # the final teardown of every remaining room: ``shutdown`` detaches
            # the rooms from the map and each is torn down with the literal
            # ``server_shutdown`` reason and no fabricated winner.
            for room in self.manager.shutdown():
                await _release_room_resources(
                    room, contract.CLOSE_REASON_SERVER_SHUTDOWN
                )
        self.manager = None
        self.endpoint = None
        self._cleanup_task = None
        self._gravity_task = None


def _publish_room_state(room: Room) -> None:
    """Broadcast BOTH authoritative boards to BOTH peers after a gravity advance.

    The gravity loop calls this (native-14 task 30.2) once a room's boards have
    advanced at a logical instant, so a server no-input gravity step reaches both
    connected peers WITHOUT requiring any recipient inbound traffic -- each
    peer's independent writer flushes the enqueued frames. Delegates to the
    shared ``broadcast_room_state`` so the endpoint and the loop produce the
    identical both-board payload.
    """

    broadcast_room_state(room)


def _publish_room_outcome(room: Room, outcome: OutcomeData) -> None:
    """Emit the terminal/forfeit ``outcome`` frame to BOTH peers (native-14).

    Wired as the gravity loop's ``on_outcome`` so a terminal/forfeit resolution
    decided by the server (no manual action) actually delivers the outcome frame
    to both connected peers, not just to a seat with inbound traffic. On the
    gravity terminal path the loop ALSO runs ``on_state`` (``_publish_room_state``)
    in the SAME step before this callback (``gravity_step`` publishes the final
    boards for a resolved room too), so both peers observe the FINAL both-board
    state immediately followed by this single ``outcome`` frame with no further
    client traffic. The disconnect / failed-send forfeit paths -- which have NO
    ``on_state`` step -- publish the equivalent final-state-then-outcome payload
    through the shared ``broadcast_terminal`` seam in the endpoint. Delegates to
    the shared ``broadcast_outcome`` builder so the outcome frame is identical
    across paths.
    """

    broadcast_outcome(room, outcome)


# ---------------------------------------------------------------------------
# Lifecycle close of a reaped / shutdown room (M3 native 19 F3, task 35.3).
#
# A room released by ``cleanup_tick`` (waiting/idle/finished retention) or by
# ``shutdown`` must NOT just be dropped from the manager map: its still-blocked
# per-connection coroutines (the reader parked on ``websocket.receive()`` and the
# independent writer parked on its wakeup signal) have to be WOKEN and its socket
# actually CLOSED with a documented standard close code + LITERAL reason, and any
# owned room-scoped task released/awaited. This reuses the SAME single ordered
# writer/socket seam task 35.2 built (``Seat.request_close`` -> the writer drains
# then closes -> ``signal_writer_gone`` wakes the blocked reader), so close
# directives flow through the one ordered writer rather than a concurrent
# unsynchronized close. A lifecycle/operational abort fabricates NO gameplay
# winner: the room is marked ``set_operational_abort_once`` FIRST so a woken
# reader's ``_handle_disconnect`` observes the abort marker and never resolves a
# forfeit on the reaped room.
# ---------------------------------------------------------------------------


#: Per-status LITERAL close reason for a reaped room (native constants /
#: design.md "Close-code mapping"). A reaped room is a lifecycle abort, never a
#: gameplay result, so no winner is fabricated for any of these.
def _reap_close_reason(status: str) -> str:
    """Return the LITERAL close reason for a reaped room of ``status``.

    * ``waiting``  -> ``waiting_room_timeout`` (a never-started room timed out).
    * ``playing``  -> ``idle_timeout`` (a started room went idle past the bound).
    * ``finished`` -> ``normal_completion`` (the duel already resolved; the
      finished retention window merely expired, so the drained terminal socket is
      closed normally -- no new winner is invented).
    """

    if status == "waiting":
        return contract.CLOSE_REASON_WAITING_ROOM_TIMEOUT
    if status == "playing":
        return contract.CLOSE_REASON_IDLE_TIMEOUT
    return contract.CLOSE_REASON_NORMAL_COMPLETION


def _reap_close_code(reason: str) -> int:
    """Return the standard close CODE for a reaped room's literal ``reason`` (D2).

    The close code is selected BY REASON, not unconditionally 1001 (the native-20
    D2 defect that closed a reaped ``finished``/``normal_completion`` room 1001):

    * ``normal_completion`` -> 1000 ``CLOSE_CODE_NORMAL``. A reaped ``finished``
      room already resolved to a gameplay outcome; its drained terminal socket is
      closed NORMALLY with the canonical 1000 code, matching the endpoint's own
      ``_finish_and_close`` normal-completion close.
    * every other lifecycle reason (``waiting_room_timeout`` / ``idle_timeout`` /
      ``server_shutdown`` and any operational abort) keeps 1001
      ``CLOSE_CODE_GOING_AWAY`` -- the already-passing waiting / idle / shutdown
      cases are unchanged.
    """

    if reason == contract.CLOSE_REASON_NORMAL_COMPLETION:
        return contract.CLOSE_CODE_NORMAL
    return contract.CLOSE_CODE_GOING_AWAY


async def _release_room_resources(room: Room, reason: str) -> None:
    """Close a reaped/shutdown room's sockets and release/await its owned task.

    Drives the WHOLE room down with NO fabricated gameplay winner:

    1. Mark the room an operational/lifecycle abort EXACTLY once (``reason`` is
       the literal lifecycle reason) so a woken reader's ``_handle_disconnect``
       sees the abort marker and does NOT resolve a forfeit on the reaped room.
       (A ``finished`` room already has an ``outcome``; the marker is a harmless
       no-op there and its terminal result stands.)
    2. For EVERY seat, request a writer-driven close with the close code SELECTED
       BY REASON (``_reap_close_code``: 1000 ``CLOSE_CODE_NORMAL`` for a reaped
       ``finished``/``normal_completion`` room, 1001 ``CLOSE_CODE_GOING_AWAY`` for
       waiting / idle / shutdown / operational aborts) + the literal reason
       through the SAME single ordered writer (``Seat.request_close``): the writer
       drains any queued frames, closes its own socket, and wakes the blocked
       reader. Also set the
       writer-gone signal directly (so an idle reader parked on ``receive`` wakes
       even if its writer already exited) and close the outbound channel (so a
       writer with no reader drains and exits without leaking a task).
    3. Release/await the room's OWNED gravity task handle, if any was attached to
       the room (production runs a single manager-wide gravity loop owned by the
       runtime, so ``room.gravity_task`` is normally ``None``; a room that owns
       its own task is cancelled and awaited here with no leak).

    Performs NO socket I/O itself and takes no manager lock: it only sets the
    seat seams; the per-connection writer performs the bounded close outside any
    lock. Safe to call on a room whose connections already tore down (the seams
    are idempotent no-ops once a seat's writer/reader has exited).
    """

    # (1) No fabricated winner: mark the lifecycle/operational abort first.
    room.set_operational_abort_once(reason)

    # (2) Wake + close every seat through the single ordered writer seam. The
    # close CODE is chosen BY REASON (D2): a reaped finished/normal_completion
    # room closes 1000, every other lifecycle reason keeps 1001.
    close_code = _reap_close_code(reason)
    for seat in room.seats.values():
        seat.request_close(close_code, reason)
        seat.signal_writer_gone()
        seat.close_outbound()

    # (3) Release/await any room-owned task (normally None in production).
    task = room.gravity_task
    if isinstance(task, asyncio.Task):
        task.cancel()
        await asyncio.wait({task})
    room.gravity_task = None


async def _cleanup_loop(manager: RoomManager) -> None:
    """Drive ``RoomManager.cleanup_tick`` periodically at the fixed cadence.

    Runs even without traffic (status-keyed retention) and exits cleanly on
    cancellation so the task is never leaked on shutdown. Each reaped room is
    removed from the manager map by ``cleanup_tick`` AND then actively torn down
    here (native-19 F3): its blocked reader/writer are woken and its socket is
    closed with the per-status literal reason through the single ordered writer
    seam, and any owned room task is released/awaited. A reaped room is a
    lifecycle abort -- it fabricates NO gameplay winner (``waiting_room_timeout``
    / ``idle_timeout`` / ``normal_completion`` for a drained finished room).
    """

    try:
        while True:
            reaped = manager.cleanup_tick()
            for room in reaped:
                await _release_room_resources(room, _reap_close_reason(room.status))
            await asyncio.sleep(CLEANUP_CADENCE)
    except asyncio.CancelledError:
        # RE-RAISE so cancellation genuinely propagates to this task instead of
        # being swallowed (native-14 S7497 lifecycle fix). ``stop`` awaits the
        # cancelled task via ``asyncio.wait`` and absorbs its expected cancel.
        raise


# The single runtime holder; (re)populated by the lifespan on each startup.
_duel_runtime = _DuelRuntime()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the solo store and the lifespan-owned duel runtime.

    Startup: initialize the High_Score_Store once (unchanged solo behavior),
    then construct the single duel ``RoomManager`` + endpoint and launch the
    periodic ``cleanup_tick`` and gravity tasks. Shutdown: cancel those tasks
    and release all duel rooms/sockets so nothing leaks across repeated
    ``TestClient`` contexts or event loops. The solo path is untouched.
    """

    store = HighScoreStore.from_env()
    store.initialize()
    deps.set_high_score_store(store)

    await _duel_runtime.start()
    try:
        yield
    finally:
        await _duel_runtime.stop()


app = FastAPI(title="Tetris Stage 3 (Option A)", lifespan=lifespan)

# Restrictive, configurable CORS. Credentials are allowed only with an explicit
# origin allow-list, never with a wildcard origin (Req 10.3, 10.4). This solo
# HTTP CORS policy is preserved exactly; the duel uses a SEPARATE WS Origin
# allow-list bound to the proxy port and never alters this middleware.
app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(games_router)
app.include_router(high_scores_router)


@app.websocket("/ws/duel")
async def duel_ws(websocket: WebSocket) -> None:
    """Serve ``/ws/duel`` via the current lifespan-owned duel endpoint.

    Resolves the endpoint from the lifespan-owned runtime at call time so no
    manager/task is created at import. If no runtime is active (a connection
    outside the lifespan), the upgrade is rejected pre-accept with a policy
    close — the same HTTP-level denial used for a disallowed Origin — rather
    than touching a stale or missing manager.
    """

    endpoint = _duel_runtime.endpoint
    if endpoint is None:
        await websocket.close(code=contract.CLOSE_CODE_POLICY)
        return
    await endpoint(websocket)


@app.get("/health")
def health() -> dict[str, str]:
    """Simple liveness check."""

    return {"status": "ok"}
