// Duel view (M3, task 32.1). An accessible two-seat duel screen built on top
// of the real standard-WebSocket duel client (`duelClient.ts`, task 31.1).
//
// Responsibilities (design.md "Duel view and mode switch"):
//   * Named-room create/join/wait/start/error/finished/return/restart flows. A
//     restart is always a FRESH room (never a reused finished room).
//   * Reuse `CanvasBoard` for BOTH authoritative boards (own + opponent). The
//     board shown is ALWAYS the latest authoritative state frame; this view
//     never predicts, mutates, or ticks a board locally.
//   * Show meaningful own and opponent status/score/lines/level/next/Hold, plus
//     the own controls. The opponent board is READ-ONLY: no control, button, or
//     key is ever wired to the opponent seat.
//   * Bind exactly one real key input to EXACTLY ONE canonical action through
//     the duel client: ArrowUp -> rotate clockwise (cw), z / Z -> rotate
//     counter-clockwise (ccw), ArrowLeft / ArrowRight -> move, ArrowDown ->
//     soft drop, and the Hold key -> hold (matching the M1 solo mapping). Each
//     is gated on the room being `playing` AND on owning the acting seat.
//
// Lifecycle safety (design.md "Lifecycle safety"):
//   * Only the OWNED duel socket/listeners/handlers are cleaned up on restart,
//     return, and unmount; nothing else is touched.
//   * There is NO solo autotick and NO solo keyboard listener here: this view
//     never imports or mounts the solo `useGame` hook. The parent `App` mounts
//     EITHER the solo view OR this duel view, never both, so switching to duel
//     tears down the solo listeners/timers and switching back tears down this
//     view's socket effect. Opening a fresh room creates a brand-new client and
//     closes the previous one, leaving no stale socket effect.
//
// Seed boundary: no production debug hook/endpoint, no React-internal access,
// no source input interception, no WebSocket/fetch monkeypatch. The only
// transport is the `DuelClient`, which owns the single real browser WebSocket.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { CanvasBoard } from "./CanvasBoard";
import { Preview } from "./Preview";
import {
  openDuelClient,
  type ActionKind,
  type DuelClient,
  type DuelClientOptions,
  type ErrorFrame,
  type OutcomeFrame,
  type PieceType,
  type RejectFrame,
  type Seat,
  type StateFrame,
  type WelcomeFrame,
} from "./duelClient";
import type { GameState } from "./types";

// A narrowed snapshot of the latest authoritative frame for ONE seat. The two
// seats' latest state frames are tracked separately and rendered independently.
interface SeatSnapshot {
  board: number[][];
  active_piece: StateFrame["active_piece"];
  next_piece: PieceType | null;
  hold_piece: PieceType | null;
  can_hold: boolean;
  score: number;
  total_lines: number;
  level: number;
  status: StateFrame["status"];
  revision: number;
}

function snapshotFromState(frame: StateFrame): SeatSnapshot {
  return {
    board: frame.board,
    active_piece: frame.active_piece,
    next_piece: frame.next_piece,
    hold_piece: frame.hold_piece,
    can_hold: frame.can_hold,
    score: frame.score,
    total_lines: frame.total_lines,
    level: frame.level,
    status: frame.status,
    revision: frame.revision,
  };
}

// An empty 20x10 board used as the visual placeholder before a seat's first
// authoritative state frame arrives (so CanvasBoard always has a real board to
// draw and never reads undefined rows).
const EMPTY_BOARD: number[][] = Array.from({ length: 20 }, () =>
  Array.from({ length: 10 }, () => 0),
);

// Adapt a seat snapshot (or absence of one) into the `GameState` shape that the
// shared CanvasBoard renderer consumes. CanvasBoard only reads `board` and
// `active_piece`, but the full shape is provided so the renderer contract is
// honored without a cast. `next_piece` on the wire may be null (e.g. a finished
// board); CanvasBoard never reads it, and the panel below reads the snapshot
// directly, so a placeholder "I" here is purely structural and never shown.
function toBoardGameState(
  seat: Seat,
  snapshot: SeatSnapshot | null,
): GameState {
  const source = snapshot ?? {
    board: EMPTY_BOARD,
    active_piece: null,
    next_piece: null,
    hold_piece: null,
    can_hold: false,
    score: 0,
    total_lines: 0,
    level: 1,
    status: "playing" as const,
    revision: 0,
  };
  return {
    id: `duel-seat-${seat}`,
    status: source.status === "game_over" ? "game_over" : "playing",
    board: source.board,
    active_piece: source.active_piece,
    score: source.score,
    total_lines: source.total_lines,
    level: source.level,
    gravity_interval_ms: 0,
    // Structural only; CanvasBoard ignores this and the visible panel reads the
    // snapshot's real `next_piece` (which may be null) directly.
    next_piece: source.next_piece ?? "I",
    hold_piece: source.hold_piece,
    can_hold: source.can_hold,
  };
}

// Map a real keyboard event to at most one canonical duel action kind. Returns
// null for any key that is not a bound control, so a non-bound key emits no
// action. This is the ONLY place a key is translated to an action kind.
function actionKindForKey(event: KeyboardEvent): ActionKind | null {
  switch (event.key) {
    case "ArrowLeft":
      return "left";
    case "ArrowRight":
      return "right";
    case "ArrowDown":
      return "down";
    case "ArrowUp":
      return "cw";
    case "z":
    case "Z":
      return "ccw";
    case "c":
    case "C":
      return "hold";
    default:
      return null;
  }
}

// The connection phase drives which flow (idle form, waiting, playing,
// finished, error) the view renders. It is derived from authoritative frames
// only; the view never fabricates a start or a finish.
type Phase = "idle" | "connecting" | "waiting" | "playing" | "finished" | "error";

export interface DuelViewProps {
  // Test seam ONLY: supply a WebSocket constructor and/or URL resolver that the
  // duel client will use, exactly as `DuelClient` accepts them. In production
  // both are undefined and the client uses the real browser globals, so there
  // is NO monkeypatch of any global here. Behaves as `DuelClientOptions`
  // without the `roomId`/`callbacks` the view supplies itself.
  clientOptions?: Pick<DuelClientOptions, "webSocketImpl" | "resolveUrl">;
  // Optional callback so the parent mode switch can request returning to solo.
  onExit?: () => void;
}

export function DuelView({ clientOptions, onExit }: Readonly<DuelViewProps>) {
  // The single owned duel client (or null when not connected). Held in a ref so
  // the keyboard handler and cleanup always see the current client without
  // re-subscribing on every state change.
  const clientRef = useRef<DuelClient | null>(null);

  const [roomInput, setRoomInput] = useState("");
  const [activeRoom, setActiveRoom] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [seat, setSeat] = useState<Seat | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Latest authoritative snapshot per seat. Routed strictly by frame seat_id so
  // A and B are never cross-wired.
  const [seatA, setSeatA] = useState<SeatSnapshot | null>(null);
  const [seatB, setSeatB] = useState<SeatSnapshot | null>(null);
  const [outcome, setOutcome] = useState<OutcomeFrame | null>(null);

  // Mirror the fields the keyboard handler must gate on into refs so the single
  // window listener added on mount reads the latest values without being torn
  // down and re-added on every state change (which could drop a keypress).
  const phaseRef = useRef<Phase>(phase);
  phaseRef.current = phase;
  const seatRef = useRef<Seat | null>(seat);
  seatRef.current = seat;

  // Close and drop ONLY the owned client. Idempotent. Never touches any other
  // socket, listener, or global.
  const closeOwnedClient = useCallback(() => {
    const client = clientRef.current;
    if (client) {
      clientRef.current = null;
      client.close();
    }
  }, []);

  // Open a fresh room: close any previously owned client first (so no stale
  // socket effect survives), reset per-connection state, and construct exactly
  // one new client whose callbacks drive the view from authoritative frames.
  const connect = useCallback(
    (roomId: string) => {
      const trimmed = roomId.trim();
      if (trimmed.length < 1) {
        setErrorMessage("Enter a room name to create or join a duel.");
        setPhase("error");
        return;
      }

      // Tear down the previous owned client BEFORE creating a new one. A
      // restart is always a fresh room; the finished client is never reused.
      closeOwnedClient();

      // Reset per-connection view state for the fresh room.
      setActiveRoom(trimmed);
      setSeat(null);
      setSeatA(null);
      setSeatB(null);
      setOutcome(null);
      setErrorMessage(null);
      setPhase("connecting");

      const client = openDuelClient({
        roomId: trimmed,
        webSocketImpl: clientOptions?.webSocketImpl,
        resolveUrl: clientOptions?.resolveUrl,
        callbacks: {
          onWelcome: (frame: WelcomeFrame) => {
            setSeat(frame.seat_id);
            // Reflect the room status the server reports: a second joiner may
            // arrive to an already-playing room.
            setPhase(frame.room_status === "playing" ? "playing" : "waiting");
          },
          onState: (frame: StateFrame) => {
            const snapshot = snapshotFromState(frame);
            if (frame.seat_id === "A") {
              setSeatA(snapshot);
            } else {
              setSeatB(snapshot);
            }
            // The room-level status drives the phase; a playing room moves the
            // view out of waiting. A finished room is only reached through the
            // outcome frame, so do not downgrade here.
            setPhase((prev) =>
              prev === "finished" || prev === "error"
                ? prev
                : frame.room_status === "playing"
                  ? "playing"
                  : frame.room_status === "finished"
                    ? "finished"
                    : "waiting",
            );
          },
          onReject: (_frame: RejectFrame) => {
            // A reject is authoritative revision bookkeeping handled inside the
            // client; the view needs no state change. Intentionally a no-op so
            // a rejected action never rolls the view back.
          },
          onError: (frame: ErrorFrame) => {
            setErrorMessage(`Duel error: ${frame.reason}`);
            setPhase("error");
          },
          onOutcome: (frame: OutcomeFrame) => {
            setOutcome(frame);
            setPhase("finished");
          },
          onClose: () => {
            // Only react to a close of the CURRENT owned client. A close event
            // from a previous (already-replaced) client must not disturb a
            // fresh connection. If the still-owned client closed while we were
            // mid-duel, surface it as a finished/returnable state.
            setPhase((prev) =>
              prev === "finished" || prev === "error" ? prev : "idle",
            );
          },
        },
      });
      clientRef.current = client;
    },
    [clientOptions, closeOwnedClient],
  );

  // Return to the room form: close the owned client and reset to idle so solo
  // stays reachable and no stale socket effect remains.
  const handleReturn = useCallback(() => {
    closeOwnedClient();
    setActiveRoom(null);
    setSeat(null);
    setSeatA(null);
    setSeatB(null);
    setOutcome(null);
    setErrorMessage(null);
    setPhase("idle");
  }, [closeOwnedClient]);

  // Restart is a FRESH room using the same entered name: close the finished
  // client and open a brand-new one. Never reuse a finished room/client.
  const handleRestart = useCallback(() => {
    const name = (activeRoom ?? roomInput).trim();
    if (name.length < 1) {
      handleReturn();
      return;
    }
    connect(name);
  }, [activeRoom, roomInput, connect, handleReturn]);

  // Emit EXACTLY ONE canonical action for an authorized local input. Gated on
  // the room being `playing` AND on owning a seat. The client itself performs
  // the seat-ownership + transport gating; this returns early so a key pressed
  // while waiting/finished/without a seat emits nothing.
  const emitAction = useCallback((kind: ActionKind) => {
    if (phaseRef.current !== "playing") {
      return;
    }
    if (seatRef.current === null) {
      return;
    }
    const client = clientRef.current;
    if (!client) {
      return;
    }
    client.sendAction(kind);
  }, []);

  // One window keyboard listener for the whole duel view, added once on mount
  // and removed on unmount. It reads the latest phase/seat via refs so it is
  // never torn down on state churn (which could drop a keypress). While this
  // view is mounted the parent does NOT mount the solo view, so there is no
  // competing solo keyboard listener.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      const kind = actionKindForKey(event);
      if (kind === null) {
        return;
      }
      // Gate before preventing default so non-playing keys keep normal behavior.
      if (phaseRef.current !== "playing" || seatRef.current === null) {
        return;
      }
      event.preventDefault();
      emitAction(kind);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [emitAction]);

  // On unmount, close ONLY the owned client so no socket/listener leaks and no
  // stale socket effect survives a mode switch back to solo.
  useEffect(() => {
    return () => {
      closeOwnedClient();
    };
  }, [closeOwnedClient]);

  const ownSeat = seat;
  const opponentSeat: Seat | null =
    ownSeat === "A" ? "B" : ownSeat === "B" ? "A" : null;

  const ownSnapshot = ownSeat === "A" ? seatA : ownSeat === "B" ? seatB : null;
  const opponentSnapshot =
    opponentSeat === "A" ? seatA : opponentSeat === "B" ? seatB : null;

  const ownBoardState = useMemo(
    () => toBoardGameState(ownSeat ?? "A", ownSnapshot),
    [ownSeat, ownSnapshot],
  );
  const opponentBoardState = useMemo(
    () => toBoardGameState(opponentSeat ?? "B", opponentSnapshot),
    [opponentSeat, opponentSnapshot],
  );

  const playing = phase === "playing";
  const canControl = playing && ownSeat !== null;
  const holdDisabled = !canControl || !(ownSnapshot?.can_hold ?? false);

  const outcomeText = outcome ? describeOutcome(outcome, ownSeat) : null;

  return (
    <section
      aria-label="Duel"
      style={{
        boxSizing: "border-box",
        width: "100%",
        maxWidth: 1180,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
      }}
    >
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}>
        <h2 style={{ margin: "4px 0", fontSize: 18 }}>Duel</h2>
        {onExit && (
          <button type="button" onClick={onExit}>
            Back to solo
          </button>
        )}
      </div>

      {phase === "idle" || phase === "error" ? (
        <form
          aria-label="Duel room"
          onSubmit={(event) => {
            event.preventDefault();
            connect(roomInput);
          }}
          style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", justifyContent: "center" }}
        >
          <label htmlFor="duel-room-name">Room name</label>
          <input
            id="duel-room-name"
            name="duel-room-name"
            type="text"
            value={roomInput}
            onChange={(event) => setRoomInput(event.target.value)}
            placeholder="room name"
            autoComplete="off"
          />
          <button type="submit">Create or join</button>
        </form>
      ) : (
        <div
          role="status"
          aria-label="Duel room status"
          data-testid="duel-room-status"
          style={{ fontSize: 14 }}
        >
          Room: {activeRoom ?? ""} - {describePhase(phase)}
          {ownSeat && <> - you are seat {ownSeat}</>}
        </div>
      )}

      {errorMessage && (
        <p role="alert" style={{ color: "#f87171", margin: "4px 0" }}>
          {errorMessage}
        </p>
      )}

      {phase === "waiting" && (
        <p role="status" data-testid="duel-waiting" style={{ margin: "4px 0" }}>
          Waiting for an opponent to join {activeRoom}...
        </p>
      )}

      {(phase === "playing" || phase === "finished") && (
        <div
          style={{
            display: "flex",
            gap: 24,
            alignItems: "flex-start",
            flexWrap: "wrap",
            justifyContent: "center",
            width: "100%",
          }}
        >
          <DuelSeatPanel
            title="Your board"
            boardLabel="Your Tetris board"
            seatLabel={ownSeat}
            snapshot={ownSnapshot}
            boardState={ownBoardState}
            testPrefix="own"
          />
          <DuelSeatPanel
            title="Opponent"
            boardLabel="Opponent Tetris board (read-only)"
            seatLabel={opponentSeat}
            snapshot={opponentSnapshot}
            boardState={opponentBoardState}
            testPrefix="opponent"
            readOnly
          />
        </div>
      )}

      {phase === "finished" && outcomeText && (
        <p
          data-testid="duel-outcome"
          style={{ fontSize: 18, fontWeight: 700, margin: "4px 0", color: "#fbbf24" }}
        >
          {outcomeText}
        </p>
      )}

      {/* Own controls. These are the ONLY controls wired to an action, and they
          always act on the OWN seat through the owned client. The opponent
          panel renders no control. */}
      {(phase === "playing" || phase === "finished") && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
          <button type="button" onClick={() => emitAction("left")} disabled={!canControl}>
            Left
          </button>
          <button type="button" onClick={() => emitAction("down")} disabled={!canControl}>
            Soft Drop
          </button>
          <button type="button" onClick={() => emitAction("right")} disabled={!canControl}>
            Right
          </button>
          <button
            type="button"
            onClick={() => emitAction("cw")}
            disabled={!canControl}
            aria-label="Rotate clockwise"
          >
            Rotate CW
          </button>
          <button
            type="button"
            onClick={() => emitAction("ccw")}
            disabled={!canControl}
            aria-label="Rotate counter-clockwise"
          >
            Rotate CCW
          </button>
          <button type="button" onClick={() => emitAction("hold")} disabled={holdDisabled}>
            Hold
          </button>
        </div>
      )}

      {phase === "finished" && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
          <button type="button" onClick={handleRestart}>
            Restart duel
          </button>
          <button type="button" onClick={handleReturn}>
            Return to room list
          </button>
        </div>
      )}

      <p style={{ fontSize: 12, opacity: 0.7, margin: "4px 0", maxWidth: 640, textAlign: "center" }}>
        Use Left / Right arrows to move, Down arrow to soft drop, Up arrow to
        rotate clockwise, Z to rotate counter-clockwise, and the C key (or Hold
        button) to hold. Controls act on your own board only; the opponent board
        is read-only.
      </p>
    </section>
  );
}

// A single seat's board + panel. `readOnly` opponent panels render no control
// (the shared controls below the boards act on the OWN seat only).
interface DuelSeatPanelProps {
  title: string;
  boardLabel: string;
  seatLabel: Seat | null;
  snapshot: SeatSnapshot | null;
  boardState: GameState;
  testPrefix: string;
  readOnly?: boolean;
}

function DuelSeatPanel({
  title,
  boardLabel,
  seatLabel,
  snapshot,
  boardState,
  testPrefix,
  readOnly = false,
}: Readonly<DuelSeatPanelProps>) {
  const statusText =
    snapshot == null
      ? "Waiting"
      : snapshot.status === "game_over"
        ? "Game over"
        : "Playing";
  return (
    <div
      aria-label={title}
      data-testid={`duel-panel-${testPrefix}`}
      data-readonly={readOnly ? "true" : "false"}
      style={{ display: "flex", gap: 12, alignItems: "flex-start" }}
    >
      <div style={{ flex: "0 0 auto", width: 240, maxWidth: 240 }}>
        <div style={{ marginBottom: 4, fontWeight: 600 }}>
          {title}
          {seatLabel ? ` (seat ${seatLabel})` : ""}
        </div>
        <div style={{ width: 240, maxWidth: 240 }} aria-label={boardLabel}>
          <CanvasBoard state={boardState} />
        </div>
      </div>
      <aside
        aria-label={`${title} status`}
        style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 130 }}
      >
        <div role="status" data-testid={`duel-status-${testPrefix}`}>
          Status: {statusText}
        </div>
        <div>
          <div data-testid={`duel-score-${testPrefix}`}>Score: {snapshot?.score ?? 0}</div>
          <div data-testid={`duel-lines-${testPrefix}`}>Lines: {snapshot?.total_lines ?? 0}</div>
          <div data-testid={`duel-level-${testPrefix}`}>Level: {snapshot?.level ?? 1}</div>
        </div>
        <div>
          <div style={{ marginBottom: 4 }}>Next</div>
          <Preview piece={snapshot?.next_piece ?? null} label={`${testPrefix} next piece`} />
        </div>
        <div>
          <div style={{ marginBottom: 4 }}>Hold</div>
          <Preview piece={snapshot?.hold_piece ?? null} label={`${testPrefix} hold piece`} />
        </div>
      </aside>
    </div>
  );
}

function describePhase(phase: Phase): string {
  switch (phase) {
    case "idle":
      return "not connected";
    case "connecting":
      return "connecting";
    case "waiting":
      return "waiting for opponent";
    case "playing":
      return "playing";
    case "finished":
      return "finished";
    case "error":
      return "error";
    default:
      return phase;
  }
}

function describeOutcome(outcome: OutcomeFrame, ownSeat: Seat | null): string {
  if (outcome.result === "draw") {
    return "Duel over: draw.";
  }
  if (outcome.result === "forfeit") {
    if (outcome.forfeiting_seat && ownSeat && outcome.forfeiting_seat === ownSeat) {
      return "Duel over: you forfeited.";
    }
    if (outcome.winning_seat && ownSeat && outcome.winning_seat === ownSeat) {
      return "Duel over: opponent forfeited. You win.";
    }
    return "Duel over: forfeit.";
  }
  // result === "win"
  if (outcome.winning_seat && ownSeat && outcome.winning_seat === ownSeat) {
    return "Duel over: you win!";
  }
  if (outcome.winning_seat && ownSeat && outcome.winning_seat !== ownSeat) {
    return "Duel over: you lose.";
  }
  return `Duel over: seat ${outcome.winning_seat ?? "?"} wins.`;
}
