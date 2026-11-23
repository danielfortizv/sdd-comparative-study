// Real standard-WebSocket duel client for the Stage 4 Option A two-seat duel
// (M3 frontend, task 31.1).
//
// This module owns EXACTLY ONE browser `WebSocket` to the same-origin
// `ws(s)://<host>/ws/duel` endpoint and the listeners it attaches to that one
// socket. It sends the `hello` handshake with the chosen `room_id` and exposes
// a typed callback stream of the inbound frames defined by the FROZEN wire
// contract (`welcome`, `state`, `ack`, `reject`, `error`, `outcome`). It emits
// EXACTLY ONE canonical `action` per authorized local input, with a
// monotonically increasing own-seat ordinal (prefix `A-`/`B-` matching the
// assigned seat) and the last authoritative OWN-board revision as
// `expected_revision`.
//
// Deliberate non-goals (seed boundary; design.md "Duel WebSocket client"):
//   * NO local-predicted board, seed, or gravity. The board a caller shows is
//     always the latest authoritative state frame; this client never mutates a
//     board locally nor advances a piece/queue/gravity on its own.
//   * NO production debug hook or endpoint, NO React-internal access, NO source
//     input interception, NO WebSocket/fetch monkeypatch, and NO auth /
//     player-name / feature outside the seed. It uses only the real browser
//     `WebSocket` constructor.
//
// Robustness rules enforced here:
//   * Stale, wrong-room, or wrong-generation frames are ignored. A "generation"
//     is this client instance: once `close()` is called the instance is dead
//     and delivers nothing further, so a late frame from an old socket can
//     never reach a newer client.
//   * A late/old `ack` never rolls back newer authority: the authoritative
//     OWN-board revision only ever advances from `state` frames (and a
//     higher-or-equal `ack` revision), and a lower `ack` revision is never
//     allowed to lower it.
//   * A and B are never cross-wired: a `state`/`ack` frame is routed strictly by
//     its own `seat_id`, and the own-board revision used for `expected_revision`
//     is taken ONLY from the assigned own seat's frames.

// ---------------------------------------------------------------------------
// Frozen wire contract types (mirror backend/app/ws/contract.py and
// .kiro/specs/tetris-stage4-option-a/contract/duel-wire.schema.json). Field
// names/shapes are matched exactly; see those files for the authoritative
// definitions.
// ---------------------------------------------------------------------------

// Only supported protocol version.
export const PROTOCOL_VERSION = 1 as const;

export type Seat = "A" | "B";
export type PieceType = "I" | "O" | "T" | "S" | "Z" | "J" | "L";
export type ActionKind = "left" | "right" | "down" | "cw" | "ccw" | "hold";
export type RoomStatus = "waiting" | "playing" | "finished";
export type BoardStatus = "playing" | "game_over";

export type RejectReason =
  | "stale_revision"
  | "future_revision"
  | "not_seat_owner"
  | "not_started"
  | "bad_type"
  | "missing_field"
  | "extra_field"
  | "rate_limited"
  | "oversize"
  | "duplicate_action_conflict";

export type ErrorReason =
  | "room_not_found"
  | "room_full"
  | "room_closed"
  | "protocol_version_unsupported"
  | "handshake_timeout"
  | "malformed_message"
  | "internal";

export type OutcomeResult = "win" | "draw" | "forfeit";

export interface ActivePiece {
  type: PieceType;
  // [row, column] anchor/origin (may be negative within bounds).
  origin: [number, number];
  // Exactly four distinct absolute on-board occupied cells.
  cells: Array<[number, number]>;
}

// --- Inbound frames ---

export interface WelcomeFrame {
  type: "welcome";
  protocol_version: 1;
  room_id: string;
  seat_id: Seat;
  room_status: RoomStatus;
}

export interface StateFrame {
  type: "state";
  protocol_version: 1;
  room_id: string;
  seat_id: Seat;
  revision: number;
  status: BoardStatus;
  room_status: RoomStatus;
  board: number[][];
  active_piece: ActivePiece | null;
  next_piece: PieceType | null;
  hold_piece: PieceType | null;
  can_hold: boolean;
  score: number;
  total_lines: number;
  level: number;
  gravity_interval_ms: number;
}

export interface AckFrame {
  type: "ack";
  protocol_version: 1;
  room_id: string;
  seat_id: Seat;
  action_id: string;
  revision: number;
  applied: true;
  no_op: boolean;
}

export interface RejectFrame {
  type: "reject";
  protocol_version: 1;
  room_id: string;
  seat_id: Seat;
  action_id: string;
  reason: RejectReason;
  authoritative_revision: number;
}

export interface ErrorFrame {
  type: "error";
  protocol_version: 1;
  room_id: string | null;
  seat_id: Seat | null;
  reason: ErrorReason;
  detail: string;
}

export interface OutcomeFrame {
  type: "outcome";
  protocol_version: 1;
  room_id: string;
  result: OutcomeResult;
  winning_seat: Seat | null;
  losing_seat: Seat | null;
  forfeiting_seat: Seat | null;
  final_revision: { A: number; B: number };
}

export type InboundFrame =
  | WelcomeFrame
  | StateFrame
  | AckFrame
  | RejectFrame
  | ErrorFrame
  | OutcomeFrame;

// --- Outbound frames ---

export interface HelloFrame {
  type: "hello";
  protocol_version: 1;
  room_id: string;
}

export interface ActionFrame {
  type: "action";
  protocol_version: 1;
  room_id: string;
  seat_id: Seat;
  action_id: string;
  expected_revision: number;
  kind: ActionKind;
}

// ---------------------------------------------------------------------------
// Callback surface. Every handler is optional; the client never assumes a
// listener exists. These callbacks are the ONLY way state leaves the client,
// and they always carry an authoritative frame (never a predicted one).
// ---------------------------------------------------------------------------

export interface DuelClientCallbacks {
  onWelcome?: (frame: WelcomeFrame) => void;
  onState?: (frame: StateFrame) => void;
  onAck?: (frame: AckFrame) => void;
  onReject?: (frame: RejectFrame) => void;
  onError?: (frame: ErrorFrame) => void;
  onOutcome?: (frame: OutcomeFrame) => void;
  // Transport-level lifecycle (not wire frames). `onClose` fires once when the
  // owned socket closes; `onSocketError` fires on a transport error event.
  onOpen?: () => void;
  onClose?: (event: CloseEvent) => void;
  onSocketError?: (event: Event) => void;
}

export interface DuelClientOptions {
  // The room to join. Length 1..64 per the contract; not re-validated here
  // beyond a minimal guard because the server is authoritative.
  roomId: string;
  callbacks?: DuelClientCallbacks;
  // Test/customisation seam ONLY: a WebSocket constructor and a base URL
  // resolver. In production both default to the real browser globals, so there
  // is NO monkeypatch of `window.WebSocket`. Tests pass a fake constructor
  // here instead of mutating any global.
  webSocketImpl?: WebSocketConstructorLike;
  // Resolve the duel endpoint URL. Defaults to the same-origin `/ws/duel`.
  resolveUrl?: () => string;
}

// Minimal structural shape of the browser `WebSocket` the client depends on.
// Declared structurally so a test double can satisfy it without extending the
// DOM lib type and without any global patch.
export interface WebSocketLike {
  readonly readyState: number;
  send(data: string): void;
  close(code?: number, reason?: string): void;
  addEventListener(type: "open", listener: (ev: Event) => void): void;
  addEventListener(type: "message", listener: (ev: MessageEvent) => void): void;
  addEventListener(type: "close", listener: (ev: CloseEvent) => void): void;
  addEventListener(type: "error", listener: (ev: Event) => void): void;
  removeEventListener(type: "open", listener: (ev: Event) => void): void;
  removeEventListener(
    type: "message",
    listener: (ev: MessageEvent) => void,
  ): void;
  removeEventListener(type: "close", listener: (ev: CloseEvent) => void): void;
  removeEventListener(type: "error", listener: (ev: Event) => void): void;
}

export type WebSocketConstructorLike = new (url: string) => WebSocketLike;

// WebSocket.OPEN is the numeric constant 1 per the WHATWG spec. Declared here
// so the client does not need the ambient DOM `WebSocket` value in scope.
const WS_OPEN = 1;

// Largest ordinal expressible by the 1..15-digit canonical grammar.
const MAX_ACTION_ORDINAL = 999999999999999;

// Default same-origin duel URL resolver: derive ws/wss from the current page
// protocol and keep the exact host (host includes port), so the URL is truly
// same-origin and reaches the backend through the reverse proxy.
function defaultResolveUrl(): string {
  const loc = globalThis.location;
  const scheme = loc && loc.protocol === "https:" ? "wss" : "ws";
  const host = loc ? loc.host : "";
  return `${scheme}://${host}/ws/duel`;
}

function defaultWebSocketImpl(): WebSocketConstructorLike {
  const impl = (globalThis as { WebSocket?: unknown }).WebSocket;
  if (typeof impl !== "function") {
    throw new Error("No WebSocket implementation available in this environment");
  }
  return impl as WebSocketConstructorLike;
}

/**
 * A single-socket duel client. Construct one per duel connection; call
 * `close()` to tear it down. Owns exactly one socket and the four listeners it
 * attaches to that socket. Never touches any other socket or global.
 */
export class DuelClient {
  private readonly roomId: string;
  private readonly callbacks: DuelClientCallbacks;
  private readonly socket: WebSocketLike;

  // The seat the server assigned to this client in the `welcome` frame. Until
  // then we have no seat and therefore cannot emit an action.
  private seat: Seat | null = null;

  // Last AUTHORITATIVE own-board revision. Advanced only by own-seat `state`
  // frames and by an own-seat `ack` whose revision is >= the current value.
  // Never lowered by a late/old `ack`. Seeded to null until the first own-seat
  // authoritative frame arrives.
  private ownRevision: number | null = null;

  // Monotonic own-seat action ordinal. The next emitted action uses
  // `ownOrdinal + 1`; it only ever increases.
  private ownOrdinal = 0;

  // Dead once `close()` is called (or the socket closes). A dead client ignores
  // every inbound frame and refuses to emit, so a late frame from this (now
  // old) generation can never drive a newer client.
  private closed = false;

  // Bound listener references so `close()` removes EXACTLY the listeners this
  // instance added, and nothing else.
  private readonly onOpenListener: (ev: Event) => void;
  private readonly onMessageListener: (ev: MessageEvent) => void;
  private readonly onCloseListener: (ev: CloseEvent) => void;
  private readonly onErrorListener: (ev: Event) => void;

  constructor(options: DuelClientOptions) {
    if (!options.roomId || options.roomId.length < 1) {
      throw new Error("roomId is required");
    }
    this.roomId = options.roomId;
    this.callbacks = options.callbacks ?? {};

    const Ctor = options.webSocketImpl ?? defaultWebSocketImpl();
    const url = (options.resolveUrl ?? defaultResolveUrl)();

    // Bind listeners once so add/remove reference the identical functions.
    this.onOpenListener = () => this.handleOpen();
    this.onMessageListener = (ev) => this.handleMessage(ev);
    this.onCloseListener = (ev) => this.handleClose(ev);
    this.onErrorListener = (ev) => this.handleSocketError(ev);

    // Construct and own exactly this one socket.
    this.socket = new Ctor(url);
    this.socket.addEventListener("open", this.onOpenListener);
    this.socket.addEventListener("message", this.onMessageListener);
    this.socket.addEventListener("close", this.onCloseListener);
    this.socket.addEventListener("error", this.onErrorListener);
  }

  /** The seat assigned by the server, or null before the welcome frame. */
  get assignedSeat(): Seat | null {
    return this.seat;
  }

  /** The last authoritative own-board revision, or null before the first. */
  get authoritativeRevision(): number | null {
    return this.ownRevision;
  }

  /** True once `close()` was called or the socket closed. */
  get isClosed(): boolean {
    return this.closed;
  }

  // --- Lifecycle ---------------------------------------------------------

  private handleOpen(): void {
    if (this.closed) {
      return;
    }
    // Send the handshake with the chosen room id. This is the ONLY thing the
    // client sends before a seat is assigned.
    const hello: HelloFrame = {
      type: "hello",
      protocol_version: PROTOCOL_VERSION,
      room_id: this.roomId,
    };
    this.rawSend(hello);
    this.callbacks.onOpen?.();
  }

  private handleClose(ev: CloseEvent): void {
    if (this.closed) {
      return;
    }
    // Mark dead and drop our listeners so nothing further is delivered, but do
    // NOT call socket.close() again (the socket is already closing/closed).
    this.closed = true;
    this.detachListeners();
    this.callbacks.onClose?.(ev);
  }

  private handleSocketError(ev: Event): void {
    if (this.closed) {
      return;
    }
    this.callbacks.onSocketError?.(ev);
  }

  /**
   * Close this client: remove ONLY our own listeners and close ONLY our own
   * socket. Idempotent. After this the client is dead and ignores every frame.
   */
  close(code?: number, reason?: string): void {
    if (this.closed) {
      return;
    }
    this.closed = true;
    this.detachListeners();
    try {
      this.socket.close(code, reason);
    } catch {
      // A close() on an already-closing/closed socket may throw in some
      // environments; the client is dead regardless.
    }
  }

  private detachListeners(): void {
    this.socket.removeEventListener("open", this.onOpenListener);
    this.socket.removeEventListener("message", this.onMessageListener);
    this.socket.removeEventListener("close", this.onCloseListener);
    this.socket.removeEventListener("error", this.onErrorListener);
  }

  // --- Inbound -----------------------------------------------------------

  private handleMessage(ev: MessageEvent): void {
    if (this.closed) {
      return;
    }
    // Only TEXT JSON frames are part of the contract; ignore anything else
    // (e.g. a binary payload) without crashing.
    if (typeof ev.data !== "string") {
      return;
    }
    let frame: unknown;
    try {
      frame = JSON.parse(ev.data);
    } catch {
      // A non-JSON payload is not a contract frame; ignore it.
      return;
    }
    if (!isRecord(frame) || typeof frame.type !== "string") {
      return;
    }
    // Ignore any frame carrying a wrong protocol version.
    if (
      "protocol_version" in frame &&
      frame.protocol_version !== PROTOCOL_VERSION
    ) {
      return;
    }

    switch (frame.type) {
      case "welcome":
        this.routeWelcome(frame as unknown as WelcomeFrame);
        return;
      case "state":
        this.routeState(frame as unknown as StateFrame);
        return;
      case "ack":
        this.routeAck(frame as unknown as AckFrame);
        return;
      case "reject":
        this.routeReject(frame as unknown as RejectFrame);
        return;
      case "error":
        this.routeError(frame as unknown as ErrorFrame);
        return;
      case "outcome":
        this.routeOutcome(frame as unknown as OutcomeFrame);
        return;
      default:
        // Unknown/echoed outbound-only type: ignore.
        return;
    }
  }

  // A frame is for THIS client's room only. A wrong-room frame is ignored so a
  // stray frame never drives this client. `error`/`outcome` with a matching (or
  // nullable, for error) room are allowed through.
  private isOwnRoom(roomId: string | null | undefined): boolean {
    return roomId === this.roomId;
  }

  private routeWelcome(frame: WelcomeFrame): void {
    if (!this.isOwnRoom(frame.room_id)) {
      return;
    }
    // Seat is assigned exactly once. Ignore any later welcome that would try to
    // re-seat (and thus cross-wire A/B).
    if (this.seat === null) {
      this.seat = frame.seat_id;
    }
    this.callbacks.onWelcome?.(frame);
  }

  private routeState(frame: StateFrame): void {
    if (!this.isOwnRoom(frame.room_id)) {
      return;
    }
    // Advance the authoritative OWN-board revision ONLY from our own seat's
    // frames (never from the opponent's), and only forward. An out-of-order or
    // duplicate older own-seat state never lowers the revision. The opponent's
    // state is still delivered to the callback so the view can render both
    // boards, but it never touches our own revision/ordinal bookkeeping.
    if (this.seat !== null && frame.seat_id === this.seat) {
      if (this.ownRevision === null || frame.revision > this.ownRevision) {
        this.ownRevision = frame.revision;
      }
    }
    this.callbacks.onState?.(frame);
  }

  private routeAck(frame: AckFrame): void {
    if (!this.isOwnRoom(frame.room_id)) {
      return;
    }
    // An ack is authority only for our OWN seat and only moves the revision
    // FORWARD. A late/old ack with a lower revision never rolls back newer
    // authority established by a state frame or a newer ack.
    if (this.seat !== null && frame.seat_id === this.seat) {
      if (this.ownRevision === null || frame.revision > this.ownRevision) {
        this.ownRevision = frame.revision;
      }
    }
    this.callbacks.onAck?.(frame);
  }

  private routeReject(frame: RejectFrame): void {
    if (!this.isOwnRoom(frame.room_id)) {
      return;
    }
    // A reject carries the server's authoritative revision. Use it to RESYNC
    // our own-board revision forward (never backward) so a subsequent action
    // carries the correct expected_revision. Only for our own seat.
    if (this.seat !== null && frame.seat_id === this.seat) {
      if (
        this.ownRevision === null ||
        frame.authoritative_revision > this.ownRevision
      ) {
        this.ownRevision = frame.authoritative_revision;
      }
    }
    this.callbacks.onReject?.(frame);
  }

  private routeError(frame: ErrorFrame): void {
    // An error frame's room_id is nullable; accept a null room (connection-level
    // error) or a matching room. A non-null wrong room is ignored.
    if (frame.room_id !== null && !this.isOwnRoom(frame.room_id)) {
      return;
    }
    this.callbacks.onError?.(frame);
  }

  private routeOutcome(frame: OutcomeFrame): void {
    if (!this.isOwnRoom(frame.room_id)) {
      return;
    }
    this.callbacks.onOutcome?.(frame);
  }

  // --- Outbound ----------------------------------------------------------

  /**
   * Emit EXACTLY ONE canonical `action` for an authorized local input.
   *
   * Returns the sent `ActionFrame`, or `null` if the action is not authorized
   * (client closed, socket not open, no seat assigned yet, no authoritative own
   * revision yet, or the ordinal would exceed the grammar maximum). The caller
   * is responsible for gating on the room being `playing`; this method does the
   * seat-ownership and transport gating.
   *
   * A single call sends at most one frame. There is no retry, no batching, and
   * no local prediction: the board is never mutated here.
   */
  sendAction(kind: ActionKind): ActionFrame | null {
    if (this.closed) {
      return null;
    }
    if (this.socket.readyState !== WS_OPEN) {
      return null;
    }
    if (this.seat === null) {
      return null;
    }
    // We must know the authoritative own-board revision to send a contract-
    // valid action (expected_revision requires strict equality server-side).
    if (this.ownRevision === null) {
      return null;
    }
    const nextOrdinal = this.ownOrdinal + 1;
    if (nextOrdinal > MAX_ACTION_ORDINAL) {
      // Ordinal space exhausted; refuse rather than wrap or reuse.
      return null;
    }

    const action: ActionFrame = {
      type: "action",
      protocol_version: PROTOCOL_VERSION,
      room_id: this.roomId,
      seat_id: this.seat,
      action_id: `${this.seat}-${nextOrdinal}`,
      expected_revision: this.ownRevision,
      kind,
    };

    // Commit the ordinal only once we have built a well-formed frame, so a
    // guard-failure above never consumes an ordinal.
    this.ownOrdinal = nextOrdinal;
    this.rawSend(action);
    return action;
  }

  private rawSend(frame: HelloFrame | ActionFrame): void {
    this.socket.send(JSON.stringify(frame));
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Convenience factory mirroring the project's functional API style. Opens one
 * duel client for `roomId` with the given callbacks and returns it.
 */
export function openDuelClient(options: DuelClientOptions): DuelClient {
  return new DuelClient(options);
}
