"""Versioned duel wire contract models (Stage 4 Option A; Req 20, 21).

This module defines the Pydantic models for the SINGLE versioned WebSocket duel
wire contract. The canonical, machine-readable contract is the JSON Schema
(Draft 2020-12) at
``.kiro/specs/tetris-stage4-option-a/contract/duel-wire.schema.json`` with a
separate valid examples corpus at ``duel-wire.examples.json``. These models MUST
conform to that schema and stay consistent with ``GameStateOut`` / ``TYPE_CODES``
in ``app/api/schemas.py``.

Design decisions encoded here (see design.md "Duel wire contract"):

* Every model sets ``model_config = ConfigDict(extra="forbid")`` so an extra
  undocumented field is rejected (maps to the ``extra_field`` reject reason /
  ``malformed_message`` error path at the protocol layer).
* ``protocol_version`` is the integer constant ``1`` on every frame.
* Each frame has an enumerated string ``type`` discriminator.
* Inbound integer fields (``protocol_version``, ``expected_revision``, and the
  inbound ``revision`` on ``Ack``) are STRICT JSON-decoded Python ints: a bool,
  a string, and a float (including a lexical ``1.0``) are rejected at runtime.
  JSON Schema ``integer`` alone may accept a mathematically integral ``1.0``, so
  this strict typing is an ADDITIONAL semantic rule enforced by a validator.
* The OUTBOUND ``protocol_version`` (the schema const ``1`` on every outbound
  frame) and each board ``CellCode`` are ALSO strict: a boolean (``True == 1``),
  a float and a string are rejected rather than silently coerced. This strict
  scalar/bool rule is targeted at those two scalars ONLY; it is NOT a global
  strict-collection mode, so a valid decoded JSON board / coordinate array still
  maps to its ``AnchorCoord`` / ``OccupiedCell`` tuples (including a negative
  anchor) and every positive example keeps parsing.
* ``action_id`` follows the canonical FULL-STRING grammar
  ``^(A|B)-([1-9][0-9]{0,14})(?![\\s\\S])``. The trailing negative lookahead
  replaces ``$`` so a trailing LF / CR / CRLF / U+2028 / U+2029 is rejected.
  Locked Pydantic 2.10.4 CANNOT compile this lookaround as its default
  Rust-backed ``Field.pattern`` (it raises the expected ``SchemaError``), so the
  IDENTICAL full-string grammar is enforced here with an explicit Python
  ``re``-backed validator, NOT weakened back to a soft ``$`` anchor.
"""

from __future__ import annotations

import re
from typing import Annotated, Dict, List, Literal, Optional, Tuple, Union

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    model_validator,
)

# ---------------------------------------------------------------------------
# Concrete bounds and operational constants (design.md; Req 20, 21, 22).
# These are declared here as the single source of truth for the contract layer;
# later M3 tasks (rooms, gravity, endpoint) import them rather than re-literal.
# ---------------------------------------------------------------------------

#: Only supported protocol version.
PROTOCOL_VERSION: int = 1

#: Inclusive string-length bounds shared by ``room_id`` and ``action_id``.
ID_MIN_LENGTH: int = 1
ID_MAX_LENGTH: int = 64

#: Largest integer exactly representable as an IEEE-754 double (2**53 - 1).
SAFE_INT_MAX: int = 9007199254740991

#: ``level`` bounds (inclusive).
LEVEL_MIN: int = 1
LEVEL_MAX: int = 100000

#: ``gravity_interval_ms`` bounds (inclusive), per max(100, 500 - 50*(level-1)).
GRAVITY_INTERVAL_MIN_MS: int = 100
GRAVITY_INTERVAL_MAX_MS: int = 500

#: Board geometry (20 rows x 10 columns, integer cell codes 0..7).
BOARD_ROWS: int = 20
BOARD_COLS: int = 10
CELL_CODE_MIN: int = 0
CELL_CODE_MAX: int = 7

#: Anchor/origin coordinate bounds (may be negative within these bounds).
ANCHOR_ROW_MIN: int = -4
ANCHOR_ROW_MAX: int = 19
ANCHOR_COL_MIN: int = -3
ANCHOR_COL_MAX: int = 9

#: Absolute occupied-cell bounds (must lie on the board).
CELL_ROW_MIN: int = 0
CELL_ROW_MAX: int = 19
CELL_COL_MIN: int = 0
CELL_COL_MAX: int = 9

#: Maximum action ordinal expressible by the 1..15-digit grammar (fifteen nines).
MAX_ACTION_ORDINAL: int = 999999999999999

#: Resource / lifecycle bounds (design.md "Duel origin, bounds, close codes").
MAX_ROOMS: int = 100
MAX_MSG_BYTES: int = 4096
ACTION_RATE_PER_SEAT: int = 20
OUTBOUND_QUEUE_DEPTH: int = 64
OUTBOUND_SEND_TIMEOUT_S: int = 5
CLEANUP_CADENCE_S: int = 1
HANDSHAKE_TIMEOUT_S: int = 10
IDLE_TIMEOUT_S: int = 60
FINISHED_ROOM_RETENTION_S: int = 15
WAITING_ROOM_RETENTION_S: int = 120

# ---------------------------------------------------------------------------
# WebSocket close codes and literal close-reason strings (design.md "Close-code
# mapping"). Codes are the STANDARD RFC 6455 codes; some reasons deliberately
# share code 1001 and are disambiguated purely by the literal reason string.
# ---------------------------------------------------------------------------

CLOSE_CODE_NORMAL: int = 1000
CLOSE_CODE_GOING_AWAY: int = 1001
CLOSE_CODE_POLICY: int = 1008
CLOSE_CODE_OVERSIZE: int = 1009
#: Wire-level invalid-UTF8 TEXT frame is failed by the transport (not the app).
CLOSE_CODE_INVALID_PAYLOAD: int = 1007

#: Literal close-reason strings (distinguish the shared 1001 reasons).
CLOSE_REASON_NORMAL_COMPLETION: str = "normal_completion"
CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT: str = "peer_unavailable_forfeit"
CLOSE_REASON_WAITING_ROOM_TIMEOUT: str = "waiting_room_timeout"
CLOSE_REASON_IDLE_TIMEOUT: str = "idle_timeout"
CLOSE_REASON_HANDSHAKE_TIMEOUT: str = "handshake_timeout"
CLOSE_REASON_SERVER_SHUTDOWN: str = "server_shutdown"
CLOSE_REASON_SCALAR_OVERFLOW: str = "scalar_overflow"
CLOSE_REASON_SEQUENCE_EXHAUSTED: str = "sequence_exhausted"
CLOSE_REASON_RATE_LIMITED: str = "rate_limited"

# ---------------------------------------------------------------------------
# Canonical action_id grammar.
#
# ``^(A|B)-([1-9][0-9]{0,14})(?![\s\S])``: seat letter, hyphen, a positive
# decimal ordinal with NO leading zeros and 1..15 digits, and NO character of
# ANY kind after the ordinal. The negative lookahead ``(?![\s\S])`` replaces
# ``$`` so a trailing line terminator (LF, CR, CRLF, U+2028, U+2029) is rejected
# -- the Draft 2020-12 ``$`` would otherwise match before a trailing terminator.
#
# Python's ``re`` matches ``$`` similarly (before a final ``\n`` and, with
# ``re.MULTILINE``, at internal line boundaries), so we do NOT rely on ``$``.
# ``re.fullmatch`` is NOT sufficient on its own either, because a pattern that
# itself contains ``$`` could still mis-anchor; we therefore reproduce the exact
# canonical lookahead semantics by compiling the FULL canonical pattern string
# WITHOUT the MULTILINE/DOTALL flags and using ``re.match`` so the leading ``^``
# and the trailing ``(?![\s\S])`` do all the anchoring. ``[\s\S]`` matches any
# character including line terminators, so the negative lookahead forbids every
# trailing character.
# ---------------------------------------------------------------------------

#: The canonical grammar, byte-for-byte identical to the schema's pattern.
ACTION_ID_PATTERN: str = r"^(A|B)-([1-9][0-9]{0,14})(?![\s\S])"

#: Compiled with NO flags (no MULTILINE, no DOTALL) so anchoring is exact.
_ACTION_ID_RE = re.compile(ACTION_ID_PATTERN)

#: Per-seat variants used when the seat prefix is pinned (ActionMessage).
_ACTION_ID_RE_SEAT = {
    "A": re.compile(r"^A-([1-9][0-9]{0,14})(?![\s\S])"),
    "B": re.compile(r"^B-([1-9][0-9]{0,14})(?![\s\S])"),
}


def _validate_action_id(value: object) -> str:
    """Enforce the canonical FULL-STRING ``action_id`` grammar.

    Rejects any non-``str`` input, any value outside the 1..64 length bound, and
    anything that does not match the canonical grammar -- including a trailing
    LF / CR / CRLF / U+2028 / U+2029, which the trailing negative lookahead
    forbids. This is the ``re``-backed equivalent of the canonical lookahead
    that locked Pydantic 2.10.4 cannot compile as a Rust ``Field.pattern``.
    """

    if not isinstance(value, str):
        raise ValueError("action_id must be a string")
    if not (ID_MIN_LENGTH <= len(value) <= ID_MAX_LENGTH):
        raise ValueError(
            f"action_id length must be {ID_MIN_LENGTH}..{ID_MAX_LENGTH}"
        )
    if _ACTION_ID_RE.match(value) is None:
        raise ValueError(
            "action_id must match the canonical grammar "
            "^(A|B)-([1-9][0-9]{0,14})(?![\\s\\S]) with no trailing character"
        )
    return value


def _strict_int(value: object) -> int:
    """Require a strict JSON-decoded Python ``int``.

    Rejects ``bool`` (``True == 1`` in Python, so it must be rejected
    explicitly), ``str``, and ``float`` (including a lexical ``1.0`` whose value
    is integral). This is the ADDITIONAL runtime semantic rule beyond JSON
    Schema ``integer``.
    """

    if isinstance(value, bool):
        raise ValueError("value must be an integer, not a boolean")
    if not isinstance(value, int):
        raise ValueError("value must be a JSON integer (int), not a float/str")
    return value


def _strict_outbound_version(value: object) -> int:
    """Require the outbound ``protocol_version`` to be the strict int const ``1``.

    OUTBOUND frames declare ``protocol_version`` as the schema const ``1``. The
    plain ``Literal[1]`` form silently accepts a boolean ``True`` (``True == 1``
    in Python) and would coerce a lexical float / string, so this BeforeValidator
    applies the SAME strict JSON-decoded-``int`` rule the inbound models already
    enforce via ``_strict_int``: a ``bool``, a ``str`` and a ``float`` (including
    a lexical ``1.0``) are rejected rather than silently coerced. The remaining
    ``Literal[1]`` annotation still pins the accepted value to the canonical
    constant ``1`` and preserves the default so outbound builders keep emitting
    the canonical version.
    """

    return _strict_int(value)


# Strict integer field types.
StrictInt = Annotated[int, BeforeValidator(_strict_int)]

#: Outbound ``protocol_version``: strict JSON int AND pinned to the const ``1``.
#: ``_strict_outbound_version`` runs first (rejecting bool/float/str), then the
#: ``Literal[1]`` constraint pins the value to the canonical constant.
OutboundProtocolVersion = Annotated[
    Literal[1], BeforeValidator(_strict_outbound_version)
]

#: Strict safe integer in 0..2**53-1 (revision, score, total_lines, final_rev).
SafeInt = Annotated[int, BeforeValidator(_strict_int), Field(ge=0, le=SAFE_INT_MAX)]

#: The canonically validated ``action_id`` string type.
ActionId = Annotated[str, BeforeValidator(_validate_action_id)]

# Enumerated literal aliases mirroring the schema enums.
PieceType = Literal["I", "O", "T", "S", "Z", "J", "L"]
Seat = Literal["A", "B"]
ActionKind = Literal["left", "right", "down", "cw", "ccw", "hold"]
RoomStatus = Literal["waiting", "playing", "finished"]
BoardStatus = Literal["playing", "game_over"]
RejectReason = Literal[
    "stale_revision",
    "future_revision",
    "not_seat_owner",
    "not_started",
    "bad_type",
    "missing_field",
    "extra_field",
    "rate_limited",
    "oversize",
    "duplicate_action_conflict",
]
ErrorReason = Literal[
    "room_not_found",
    "room_full",
    "room_closed",
    "protocol_version_unsupported",
    "handshake_timeout",
    "malformed_message",
    "internal",
]
OutcomeResult = Literal["win", "draw", "forfeit"]

# Coordinate / board field types with the exact schema bounds.
AnchorRow = Annotated[int, Field(ge=ANCHOR_ROW_MIN, le=ANCHOR_ROW_MAX)]
AnchorCol = Annotated[int, Field(ge=ANCHOR_COL_MIN, le=ANCHOR_COL_MAX)]
CellRow = Annotated[int, Field(ge=CELL_ROW_MIN, le=CELL_ROW_MAX)]
CellCol = Annotated[int, Field(ge=CELL_COL_MIN, le=CELL_COL_MAX)]
AnchorCoord = Tuple[AnchorRow, AnchorCol]
OccupiedCell = Tuple[CellRow, CellCol]
#: A board cell code is a strict JSON int in 0..7. The ``_strict_int``
#: BeforeValidator rejects a boolean cell (``True``/``False``) rather than
#: silently coercing it to ``1``/``0``; it is applied ONLY to this scalar cell
#: code, NOT to the coordinate tuple element ints, so valid decoded JSON arrays
#: still map to ``AnchorCoord`` / ``OccupiedCell`` tuples (including negative
#: anchors) and every positive example keeps parsing.
CellCode = Annotated[
    int, BeforeValidator(_strict_int), Field(ge=CELL_CODE_MIN, le=CELL_CODE_MAX)
]
RoomId = Annotated[str, Field(min_length=ID_MIN_LENGTH, max_length=ID_MAX_LENGTH)]
Level = Annotated[int, BeforeValidator(_strict_int), Field(ge=LEVEL_MIN, le=LEVEL_MAX)]
GravityIntervalMs = Annotated[
    int,
    BeforeValidator(_strict_int),
    Field(ge=GRAVITY_INTERVAL_MIN_MS, le=GRAVITY_INTERVAL_MAX_MS),
]
Detail = Annotated[str, Field(max_length=200)]


class _WireModel(BaseModel):
    """Common base: forbid extra fields on every wire frame."""

    model_config = ConfigDict(extra="forbid")


class ActivePiece(_WireModel):
    """Active (falling) piece.

    ``origin`` is an anchor coordinate (may be negative within bounds); ``cells``
    holds EXACTLY four DISTINCT absolute on-board occupied cells. Matches the
    solo ``ActivePieceOut`` ``type``/``origin``/``cells`` shape.
    """

    type: PieceType
    origin: AnchorCoord
    cells: List[OccupiedCell] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def _four_distinct_cells(self) -> "ActivePiece":
        if len({tuple(cell) for cell in self.cells}) != 4:
            raise ValueError("active_piece.cells must be four DISTINCT cells")
        return self


# ---------------------------------------------------------------------------
# Inbound models.
# ---------------------------------------------------------------------------


class Hello(_WireModel):
    """Inbound handshake.

    Intentionally has NO ``client_name`` field and NO authentication: there is no
    player-name collection. ``extra="forbid"`` rejects ``client_name`` or any
    other undocumented field.
    """

    type: Literal["hello"]
    protocol_version: Annotated[int, BeforeValidator(_strict_int)]
    room_id: RoomId

    @model_validator(mode="after")
    def _version_const(self) -> "Hello":
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError(f"protocol_version must be {PROTOCOL_VERSION}")
        return self


class ActionMessage(_WireModel):
    """Inbound player action targeting the sender's own seat.

    ``action_id`` follows the canonical grammar AND its seat prefix MUST equal
    ``seat_id`` (per-seat prefix rule). ``expected_revision`` is a strict safe
    integer.
    """

    type: Literal["action"]
    protocol_version: Annotated[int, BeforeValidator(_strict_int)]
    room_id: RoomId
    seat_id: Seat
    action_id: ActionId
    expected_revision: SafeInt
    kind: ActionKind

    @model_validator(mode="after")
    def _version_and_seat_prefix(self) -> "ActionMessage":
        if self.protocol_version != PROTOCOL_VERSION:
            raise ValueError(f"protocol_version must be {PROTOCOL_VERSION}")
        if _ACTION_ID_RE_SEAT[self.seat_id].match(self.action_id) is None:
            raise ValueError(
                "action_id prefix must equal seat_id "
                f"(expected prefix '{self.seat_id}-')"
            )
        return self


# ---------------------------------------------------------------------------
# Outbound models.
# ---------------------------------------------------------------------------


class Welcome(_WireModel):
    """Outbound acceptance of a hello; assigns the seat, reports room status."""

    type: Literal["welcome"]
    protocol_version: OutboundProtocolVersion = PROTOCOL_VERSION
    room_id: RoomId
    seat_id: Seat
    room_status: RoomStatus


class StateFrame(_WireModel):
    """Outbound authoritative per-seat state snapshot at a given ``revision``.

    ``room_status`` (room lifecycle: waiting/playing/finished) is REQUIRED on
    EVERY state frame and is distinct from the per-seat board ``status``
    (playing/game_over). Board/active-piece/queue/Hold fields mirror
    ``GameStateOut`` + ``TYPE_CODES``. The status/active_piece relationship is
    enforced: ``playing`` => non-null active piece; ``game_over`` => null.
    """

    type: Literal["state"]
    protocol_version: OutboundProtocolVersion = PROTOCOL_VERSION
    room_id: RoomId
    seat_id: Seat
    revision: SafeInt
    status: BoardStatus
    room_status: RoomStatus
    board: List[List[CellCode]] = Field(min_length=BOARD_ROWS, max_length=BOARD_ROWS)
    active_piece: Optional[ActivePiece]
    next_piece: Optional[PieceType]
    hold_piece: Optional[PieceType]
    can_hold: bool
    score: SafeInt
    total_lines: SafeInt
    level: Level
    gravity_interval_ms: GravityIntervalMs

    @model_validator(mode="after")
    def _board_shape_and_status(self) -> "StateFrame":
        for row in self.board:
            if len(row) != BOARD_COLS:
                raise ValueError(f"each board row must have {BOARD_COLS} columns")
        if self.status == "playing" and self.active_piece is None:
            raise ValueError("a playing state frame must carry a non-null active_piece")
        if self.status == "game_over" and self.active_piece is not None:
            raise ValueError("a game_over state frame must carry a null active_piece")
        return self


class Ack(_WireModel):
    """Outbound acknowledgement correlated to an ``action_id``.

    An ``ack`` is ALWAYS an acceptance: ``applied`` is the const ``True``. For an
    accepted state change ``no_op=False`` with the NEW revision; for a legal
    no-op ``no_op=True`` with the UNCHANGED revision.
    """

    type: Literal["ack"]
    protocol_version: OutboundProtocolVersion = PROTOCOL_VERSION
    room_id: RoomId
    seat_id: Seat
    action_id: ActionId
    revision: SafeInt
    applied: Literal[True] = True
    no_op: bool


class Reject(_WireModel):
    """Outbound rejection of an action, correlated to ``action_id``.

    ``reason`` is one of the enumerated stable codes (which include
    ``not_started`` and ``duplicate_action_conflict`` and intentionally EXCLUDE
    ``unknown_action_id``). The ``action_id`` grammar is enforced but the prefix
    is NOT tied to ``seat_id`` here (a ``not_seat_owner`` reject may echo an
    action id whose prefix differs from the targeted seat).
    """

    type: Literal["reject"]
    protocol_version: OutboundProtocolVersion = PROTOCOL_VERSION
    room_id: RoomId
    seat_id: Seat
    action_id: ActionId
    reason: RejectReason
    authoritative_revision: SafeInt


class ErrorFrame(_WireModel):
    """Outbound connection/room-level error.

    Has NO ``action_id`` (it is the correlation-free vehicle for an uncorrelatable
    ``malformed_message``). ``room_id`` and ``seat_id`` are nullable ONLY here.
    ``detail`` is a short English string (<= 200 chars) with no path/SQL/exception
    /stack.
    """

    type: Literal["error"]
    protocol_version: OutboundProtocolVersion = PROTOCOL_VERSION
    room_id: Optional[RoomId]
    seat_id: Optional[Seat]
    reason: ErrorReason
    detail: Detail


class Outcome(_WireModel):
    """Outbound terminal duel result with per-result seat relationships.

    * ``win``: winning_seat and losing_seat are two DISTINCT seats; forfeiting
      null.
    * ``draw``: all three seat fields null.
    * ``forfeit``: forfeiting_seat == losing_seat; winning_seat is the other seat.
    """

    type: Literal["outcome"]
    protocol_version: OutboundProtocolVersion = PROTOCOL_VERSION
    room_id: RoomId
    result: OutcomeResult
    winning_seat: Optional[Seat]
    losing_seat: Optional[Seat]
    forfeiting_seat: Optional[Seat]
    final_revision: "FinalRevision"

    @model_validator(mode="after")
    def _result_seat_relationship(self) -> "Outcome":
        win, lose, forfeit = self.winning_seat, self.losing_seat, self.forfeiting_seat
        if self.result == "win":
            if forfeit is not None:
                raise ValueError("win: forfeiting_seat must be null")
            if win is None or lose is None or win == lose:
                raise ValueError("win: winning_seat and losing_seat must be two distinct seats")
        elif self.result == "draw":
            if win is not None or lose is not None or forfeit is not None:
                raise ValueError("draw: all seat fields must be null")
        elif self.result == "forfeit":
            if forfeit is None or lose is None or win is None:
                raise ValueError("forfeit: winning/losing/forfeiting seats must be present")
            if lose != forfeit:
                raise ValueError("forfeit: losing_seat must equal forfeiting_seat")
            if win == forfeit:
                raise ValueError("forfeit: winning_seat must be the other (surviving) seat")
        return self


class FinalRevision(_WireModel):
    """Per-seat final revision map, each a strict safe integer."""

    A: SafeInt
    B: SafeInt


Outcome.model_rebuild()


#: Discriminated union of every wire frame (mirrors the schema top-level oneOf).
WireMessage = Union[
    Hello,
    ActionMessage,
    Welcome,
    StateFrame,
    Ack,
    Reject,
    ErrorFrame,
    Outcome,
]


__all__ = [
    # Models
    "ActivePiece",
    "Hello",
    "ActionMessage",
    "Welcome",
    "StateFrame",
    "Ack",
    "Reject",
    "ErrorFrame",
    "Outcome",
    "FinalRevision",
    "WireMessage",
    # Grammar helpers
    "ACTION_ID_PATTERN",
    # Bounds / constants
    "PROTOCOL_VERSION",
    "ID_MIN_LENGTH",
    "ID_MAX_LENGTH",
    "SAFE_INT_MAX",
    "LEVEL_MIN",
    "LEVEL_MAX",
    "GRAVITY_INTERVAL_MIN_MS",
    "GRAVITY_INTERVAL_MAX_MS",
    "BOARD_ROWS",
    "BOARD_COLS",
    "MAX_ACTION_ORDINAL",
    "MAX_ROOMS",
    "MAX_MSG_BYTES",
    "ACTION_RATE_PER_SEAT",
    "OUTBOUND_QUEUE_DEPTH",
    "OUTBOUND_SEND_TIMEOUT_S",
    "CLEANUP_CADENCE_S",
    "HANDSHAKE_TIMEOUT_S",
    "IDLE_TIMEOUT_S",
    "FINISHED_ROOM_RETENTION_S",
    "WAITING_ROOM_RETENTION_S",
    # Close codes / reasons
    "CLOSE_CODE_NORMAL",
    "CLOSE_CODE_GOING_AWAY",
    "CLOSE_CODE_POLICY",
    "CLOSE_CODE_OVERSIZE",
    "CLOSE_CODE_INVALID_PAYLOAD",
    "CLOSE_REASON_NORMAL_COMPLETION",
    "CLOSE_REASON_PEER_UNAVAILABLE_FORFEIT",
    "CLOSE_REASON_WAITING_ROOM_TIMEOUT",
    "CLOSE_REASON_IDLE_TIMEOUT",
    "CLOSE_REASON_HANDSHAKE_TIMEOUT",
    "CLOSE_REASON_SERVER_SHUTDOWN",
    "CLOSE_REASON_SCALAR_OVERFLOW",
    "CLOSE_REASON_SEQUENCE_EXHAUSTED",
    "CLOSE_REASON_RATE_LIMITED",
]
