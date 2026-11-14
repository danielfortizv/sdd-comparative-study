// Minimal render/smoke coverage for the duel view and the solo/duel mode
// switch (task 32.1). The FULL behavioral duel suite (exact action counts,
// late-ACK no-rollback, cross-wiring, race/cleanup matrices with the triggering
// input OUTSIDE waitFor) is task 32.2; this file only proves the view renders,
// the mode switch mounts exactly one view, both authoritative boards render
// from state frames, and a single key emits exactly one canonical action while
// playing and none while waiting.
//
// These are SELF-TESTS only (never production wire/pixel/focus/performance
// proof). The fake WebSocket is passed through the view's explicit
// `clientOptions.webSocketImpl` seam; there is NO global WebSocket/fetch
// monkeypatch and NO source interception.

import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { DuelView } from "./DuelView";
import * as api from "./api";
import type { GameState } from "./types";

// A minimal in-memory fake WebSocket driven synchronously by the test. It
// implements only the structural surface the duel client depends on.
class FakeWebSocket {
  static readonly OPEN = 1;
  readyState = 0;
  readonly url: string;
  readonly sent: string[] = [];
  closeCalls = 0;
  private listeners: Record<string, Array<(ev: unknown) => void>> = {
    open: [],
    message: [],
    close: [],
    error: [],
  };

  constructor(url: string) {
    this.url = url;
  }
  send(data: string): void {
    this.sent.push(data);
  }
  close(): void {
    this.closeCalls += 1;
    this.readyState = 3;
  }
  addEventListener(type: string, listener: (ev: unknown) => void): void {
    this.listeners[type].push(listener);
  }
  removeEventListener(type: string, listener: (ev: unknown) => void): void {
    const arr = this.listeners[type];
    const idx = arr.indexOf(listener);
    if (idx >= 0) arr.splice(idx, 1);
  }
  listenerCount(): number {
    return (
      this.listeners.open.length +
      this.listeners.message.length +
      this.listeners.close.length +
      this.listeners.error.length
    );
  }
  fireOpen(): void {
    this.readyState = FakeWebSocket.OPEN;
    for (const l of [...this.listeners.open]) l(new Event("open"));
  }
  fireMessage(data: unknown): void {
    const payload = typeof data === "string" ? data : JSON.stringify(data);
    for (const l of [...this.listeners.message]) l({ data: payload });
  }
}

function makeFactory() {
  const instances: FakeWebSocket[] = [];
  const Ctor = class extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      instances.push(this);
    }
  };
  return { Ctor: Ctor as unknown as new (url: string) => FakeWebSocket, instances };
}

function stateFrame(
  seat: "A" | "B",
  revision: number,
  roomId = "room-1",
  roomStatus: "waiting" | "playing" | "finished" = "playing",
) {
  return {
    type: "state",
    protocol_version: 1,
    room_id: roomId,
    seat_id: seat,
    revision,
    status: "playing",
    room_status: roomStatus,
    board: Array.from({ length: 20 }, () => Array.from({ length: 10 }, () => 0)),
    active_piece: { type: "T", origin: [0, 3], cells: [[0, 4], [1, 3], [1, 4], [1, 5]] },
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
    score: seat === "A" ? 100 : 200,
    total_lines: seat === "A" ? 1 : 2,
    level: 1,
    gravity_interval_ms: 500,
  };
}

function welcomeFrame(seat: "A" | "B", roomStatus: "waiting" | "playing" = "waiting") {
  return {
    type: "welcome",
    protocol_version: 1,
    room_id: "room-1",
    seat_id: seat,
    room_status: roomStatus,
  };
}

// Drive a fresh client all the way to a playing room as seat A.
function connectAndPlay() {
  const factory = makeFactory();
  render(
    <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
  );
  fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
  const socket = factory.instances[0];
  act(() => {
    socket.fireOpen();
    socket.fireMessage(welcomeFrame("A", "waiting"));
    socket.fireMessage(stateFrame("A", 1));
    socket.fireMessage(stateFrame("B", 1));
  });
  return { factory, socket };
}

function solo(overrides: Partial<GameState> = {}): GameState {
  return {
    id: "game-1",
    status: "playing",
    board: Array.from({ length: 20 }, () => Array.from({ length: 10 }, () => 0)),
    active_piece: { type: "T", origin: [0, 3], cells: [[0, 4], [1, 3], [1, 4], [1, 5]] },
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
    ...overrides,
  };
}

describe("solo/duel mode switch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "createGame").mockResolvedValue(solo());
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts in solo and keeps solo reachable via the switch", async () => {
    render(<App />);
    await screen.findByTestId("score"); // solo view mounted
    expect(screen.getByTestId("mode-solo")).toBeDisabled();
    expect(screen.getByTestId("mode-duel")).toBeEnabled();

    fireEvent.click(screen.getByTestId("mode-duel"));
    expect(screen.getByLabelText("Room name")).toBeInTheDocument();
    // Solo panel is unmounted while in duel (no hidden solo view).
    expect(screen.queryByTestId("score")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("mode-solo"));
    await screen.findByTestId("score"); // solo reachable again
  });
});

describe("DuelView render and input", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the room form before connecting", () => {
    const factory = makeFactory();
    render(<DuelView clientOptions={{ webSocketImpl: factory.Ctor }} />);
    expect(screen.getByLabelText("Room name")).toBeInTheDocument();
    expect(factory.instances).toHaveLength(0);
  });

  it("renders both authoritative boards and panels once playing", () => {
    connectAndPlay();
    expect(screen.getByTestId("duel-panel-own")).toBeInTheDocument();
    expect(screen.getByTestId("duel-panel-opponent")).toBeInTheDocument();
    // Own seat is A (score 100); opponent is B (score 200).
    expect(screen.getByTestId("duel-score-own")).toHaveTextContent("Score: 100");
    expect(screen.getByTestId("duel-score-opponent")).toHaveTextContent("Score: 200");
    expect(screen.getByTestId("duel-panel-opponent")).toHaveAttribute("data-readonly", "true");
    expect(screen.getByTestId("duel-panel-own")).toHaveAttribute("data-readonly", "false");
  });

  it("emits exactly one canonical action for one key while playing", () => {
    const { socket } = connectAndPlay();
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    const actions = socket.sent.slice(before).map((s) => JSON.parse(s));
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({
      type: "action",
      seat_id: "A",
      kind: "left",
      action_id: "A-1",
      expected_revision: 1,
    });
  });

  it("emits no action while waiting (start gating)", () => {
    const factory = makeFactory();
    render(<DuelView clientOptions={{ webSocketImpl: factory.Ctor }} />);
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const socket = factory.instances[0];
    act(() => {
      socket.fireOpen();
      socket.fireMessage(welcomeFrame("A", "waiting"));
    });
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    const actions = socket.sent.slice(before).map((s) => JSON.parse(s));
    expect(actions.filter((a) => a.type === "action")).toHaveLength(0);
  });

  it("closes only the owned socket on unmount", () => {
    const factory = makeFactory();
    const { unmount } = render(
      <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
    );
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const socket = factory.instances[0];
    act(() => {
      socket.fireOpen();
    });
    expect(factory.instances).toHaveLength(1);
    unmount();
    expect(socket.closeCalls).toBe(1);
  });

  it("opens a fresh socket on restart and closes the finished one", async () => {
    const factory = makeFactory();
    render(
      <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
    );
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const first = factory.instances[0];
    act(() => {
      first.fireOpen();
      first.fireMessage(welcomeFrame("A", "playing"));
      first.fireMessage(stateFrame("A", 1));
      first.fireMessage(stateFrame("B", 1));
      first.fireMessage({
        type: "outcome",
        protocol_version: 1,
        room_id: "room-1",
        result: "win",
        winning_seat: "A",
        losing_seat: "B",
        forfeiting_seat: null,
        final_revision: { A: 1, B: 1 },
      });
    });
    await screen.findByTestId("duel-outcome");
    fireEvent.click(screen.getByRole("button", { name: "Restart duel" }));
    // A second socket was created and the first was closed (fresh room, never
    // reused).
    expect(factory.instances.length).toBe(2);
    expect(first.closeCalls).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Task 32.2 extension: the FULL meaningful behavioral duel-view suite. These
// extend the smoke tests above with the correction's explicitly required
// production-visible paths, each driving REAL DOM events / authoritative frames
// with the triggering input performed OUTSIDE any waitFor and asserting EXACT
// action counts or exact wire shapes:
//   * one-input-one-action with monotonic ordinals and the last own revision;
//   * both boards render strictly by seat_id (no A/B cross-wiring), from seat B
//     perspective too;
//   * old/late-ACK never rolls the view's authority back (next action still
//     carries the newer revision);
//   * stale / wrong-room / wrong-generation frames are ignored by the view;
//   * the error path surfaces an alert and gates input off;
//   * the start/sync path: waiting -> playing only on the authoritative frame;
//   * mode-switch / restart / unmount cleanup proving no leaked socket or
//     listener, NO solo autotick or solo keyboard listener while in duel, and
//     no stale socket after a fresh room.
// All fakes go through the explicit `clientOptions.webSocketImpl` seam; there
// is NO global WebSocket/fetch monkeypatch and NO source interception. These
// are SELF-TESTS only, never production wire/pixel/focus/performance proof.
// ---------------------------------------------------------------------------

function ackFrame(
  seat: "A" | "B",
  actionId: string,
  revision: number,
  roomId = "room-1",
) {
  return {
    type: "ack",
    protocol_version: 1,
    room_id: roomId,
    seat_id: seat,
    action_id: actionId,
    revision,
    applied: true,
    no_op: false,
  };
}

function rejectFrame(
  seat: "A" | "B",
  actionId: string,
  authoritativeRevision: number,
  roomId = "room-1",
) {
  return {
    type: "reject",
    protocol_version: 1,
    room_id: roomId,
    seat_id: seat,
    action_id: actionId,
    reason: "stale_revision",
    authoritative_revision: authoritativeRevision,
  };
}

function errorFrame(reason = "room_full", roomId: string | null = "room-1") {
  return {
    type: "error",
    protocol_version: 1,
    room_id: roomId,
    seat_id: null,
    reason,
    detail: "nope",
  };
}

// Connect a fresh view and drive it to playing as the given OWN seat.
function connectAndPlayAs(ownSeat: "A" | "B") {
  const factory = makeFactory();
  render(
    <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
  );
  fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
  fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
  const socket = factory.instances[0];
  act(() => {
    socket.fireOpen();
    socket.fireMessage(welcomeFrame(ownSeat, "playing"));
    socket.fireMessage(stateFrame("A", 1));
    socket.fireMessage(stateFrame("B", 1));
  });
  return { factory, socket };
}

function actionSends(socket: FakeWebSocket, fromIndex: number) {
  return socket.sent
    .slice(fromIndex)
    .map((s) => JSON.parse(s) as Record<string, unknown>)
    .filter((f) => f.type === "action");
}

describe("DuelView one-input-one-action and monotonic ordinals", () => {
  afterEach(() => vi.restoreAllMocks());

  it("emits exactly one canonical action per key with increasing own ordinals and the last own revision", () => {
    const { socket } = connectAndPlay(); // own seat A, own revision 1
    const before = socket.sent.length;

    // Each key fired ONCE, OUTSIDE any waitFor.
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    fireEvent.keyDown(window, { key: "ArrowRight" });
    fireEvent.keyDown(window, { key: "ArrowUp" });

    const actions = actionSends(socket, before);
    expect(actions).toHaveLength(3);
    expect(actions.map((a) => a.action_id)).toEqual(["A-1", "A-2", "A-3"]);
    expect(actions.map((a) => a.kind)).toEqual(["left", "right", "cw"]);
    // All carry the last authoritative OWN revision (1) and the own seat.
    expect(actions.every((a) => a.expected_revision === 1)).toBe(true);
    expect(actions.every((a) => a.seat_id === "A")).toBe(true);
  });

  // Direction mapping (M3 correction, task 36.2): a real ArrowUp key emits
  // EXACTLY ONE `cw` action and a real z / Z key emits EXACTLY ONE `ccw`
  // action, matching the corrected M1 solo mapping (production fix in task
  // 36.1). Each triggering key is fired ONCE, OUTSIDE any waitFor, and both the
  // exact direction and the exact count (1) are asserted. These are SELF-TESTS
  // only (never production wire/pixel/focus/performance proof).
  it("a real ArrowUp key emits exactly one cw action", () => {
    const { socket } = connectAndPlay(); // own seat A, own revision 1
    const before = socket.sent.length;

    // Triggering input OUTSIDE any waitFor, fired exactly once.
    fireEvent.keyDown(window, { key: "ArrowUp" });

    const actions = actionSends(socket, before);
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({
      type: "action",
      seat_id: "A",
      kind: "cw",
      action_id: "A-1",
      expected_revision: 1,
    });
  });

  it("a real z key emits exactly one ccw action", () => {
    const { socket } = connectAndPlay(); // own seat A, own revision 1
    const before = socket.sent.length;

    // Triggering input OUTSIDE any waitFor, fired exactly once.
    fireEvent.keyDown(window, { key: "z" });

    const actions = actionSends(socket, before);
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({
      type: "action",
      seat_id: "A",
      kind: "ccw",
      action_id: "A-1",
      expected_revision: 1,
    });
  });

  it("a real Z key (shifted) emits exactly one ccw action", () => {
    const { socket } = connectAndPlay(); // own seat A, own revision 1
    const before = socket.sent.length;

    // Triggering input OUTSIDE any waitFor, fired exactly once.
    fireEvent.keyDown(window, { key: "Z" });

    const actions = actionSends(socket, before);
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({
      type: "action",
      seat_id: "A",
      kind: "ccw",
      action_id: "A-1",
      expected_revision: 1,
    });
  });

  it("the C key emits exactly one hold action and a non-bound key emits none", () => {
    const { socket } = connectAndPlay();
    const before = socket.sent.length;

    fireEvent.keyDown(window, { key: "c" });
    fireEvent.keyDown(window, { key: "x" }); // not a bound control

    const actions = actionSends(socket, before);
    expect(actions).toHaveLength(1);
    expect(actions[0].kind).toBe("hold");
  });

  it("a single on-screen control click emits exactly one action on the OWN seat", () => {
    const { socket } = connectAndPlay();
    const before = socket.sent.length;

    fireEvent.click(screen.getByRole("button", { name: "Rotate counter-clockwise" }));

    const actions = actionSends(socket, before);
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({ kind: "ccw", seat_id: "A", action_id: "A-1" });
  });
});

describe("DuelView both boards render strictly by seat (no A/B cross-wiring)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("as seat A: own panel shows A's numbers, opponent panel shows B's; actions target A", () => {
    const { socket } = connectAndPlayAs("A");
    expect(screen.getByTestId("duel-score-own")).toHaveTextContent("Score: 100");
    expect(screen.getByTestId("duel-lines-own")).toHaveTextContent("Lines: 1");
    expect(screen.getByTestId("duel-score-opponent")).toHaveTextContent("Score: 200");
    expect(screen.getByTestId("duel-lines-opponent")).toHaveTextContent("Lines: 2");
    expect(screen.getByTestId("duel-panel-opponent")).toHaveAttribute("data-readonly", "true");

    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before)[0].seat_id).toBe("A");
  });

  it("as seat B: own panel shows B's numbers, opponent panel shows A's; actions target B", () => {
    const { socket } = connectAndPlayAs("B");
    // Own is now B (score 200); opponent is A (score 100).
    expect(screen.getByTestId("duel-score-own")).toHaveTextContent("Score: 200");
    expect(screen.getByTestId("duel-lines-own")).toHaveTextContent("Lines: 2");
    expect(screen.getByTestId("duel-score-opponent")).toHaveTextContent("Score: 100");
    expect(screen.getByTestId("duel-lines-opponent")).toHaveTextContent("Lines: 1");

    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowRight" });
    const actions = actionSends(socket, before);
    expect(actions).toHaveLength(1);
    expect(actions[0]).toMatchObject({ seat_id: "B", kind: "right", action_id: "B-1" });
  });

  it("an opponent-seat state updates ONLY the opponent panel, never the own authority/ordinal", () => {
    const { socket } = connectAndPlayAs("A");
    // A newer opponent (B) state refreshes only the opponent panel.
    act(() => {
      socket.fireMessage(
        { ...stateFrame("B", 2), score: 555, total_lines: 9 },
      );
    });
    expect(screen.getByTestId("duel-score-opponent")).toHaveTextContent("Score: 555");
    expect(screen.getByTestId("duel-score-own")).toHaveTextContent("Score: 100");

    // The own action still carries OWN authority (revision 1 from own state),
    // unaffected by the opponent's revision 2.
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before)[0].expected_revision).toBe(1);
  });
});

describe("DuelView old/late-ACK and resync authority", () => {
  afterEach(() => vi.restoreAllMocks());

  it("an own state advances authority; a later stale ack never rolls the next action back", () => {
    const { socket } = connectAndPlayAs("A");
    // Advance own authority to revision 6 via an own state frame.
    act(() => socket.fireMessage(stateFrame("A", 6)));

    const before1 = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" }); // A-1 @ 6
    expect(actionSends(socket, before1)[0].expected_revision).toBe(6);

    // A stale ack for an older revision must NOT roll back the view's authority.
    act(() => socket.fireMessage(ackFrame("A", "A-1", 2)));

    const before2 = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowRight" }); // A-2 @ 6 (not 2)
    const a2 = actionSends(socket, before2)[0];
    expect(a2.action_id).toBe("A-2");
    expect(a2.expected_revision).toBe(6);
  });

  it("a reject resyncs authority forward and the next action uses the resynced revision", () => {
    const { socket } = connectAndPlayAs("A"); // own revision 1
    const before1 = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowUp" }); // A-1 @ 1
    expect(actionSends(socket, before1)[0].expected_revision).toBe(1);

    act(() => socket.fireMessage(rejectFrame("A", "A-1", 20)));

    const before2 = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowDown" }); // A-2 @ 20
    const a2 = actionSends(socket, before2)[0];
    expect(a2.action_id).toBe("A-2");
    expect(a2.expected_revision).toBe(20);
  });
});

describe("DuelView stale / wrong-room / wrong-generation frame rejection", () => {
  afterEach(() => vi.restoreAllMocks());

  it("ignores a wrong-room state: neither panel changes and own authority is untouched", () => {
    const { socket } = connectAndPlayAs("A");
    act(() => {
      socket.fireMessage(
        { ...stateFrame("A", 999, "other-room"), score: 7777 },
      );
      socket.fireMessage(
        { ...stateFrame("B", 999, "other-room"), score: 8888 },
      );
    });
    // Panels keep their room-1 numbers.
    expect(screen.getByTestId("duel-score-own")).toHaveTextContent("Score: 100");
    expect(screen.getByTestId("duel-score-opponent")).toHaveTextContent("Score: 200");
    // Own authority stayed at 1 (wrong-room never advanced it).
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before)[0].expected_revision).toBe(1);
  });

  it("ignores a stale older own-seat state: authority never regresses below the newest", () => {
    const { socket } = connectAndPlayAs("A");
    act(() => socket.fireMessage(stateFrame("A", 9))); // authority -> 9
    act(() => socket.fireMessage(stateFrame("A", 3))); // stale, ignored
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before)[0].expected_revision).toBe(9);
  });

  it("a frame fired on a previous-generation socket never drives the fresh room after restart", async () => {
    const factory = makeFactory();
    render(
      <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
    );
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const first = factory.instances[0];
    act(() => {
      first.fireOpen();
      first.fireMessage(welcomeFrame("A", "playing"));
      first.fireMessage(stateFrame("A", 1));
      first.fireMessage(stateFrame("B", 1));
      first.fireMessage({
        type: "outcome",
        protocol_version: 1,
        room_id: "room-1",
        result: "win",
        winning_seat: "A",
        losing_seat: "B",
        forfeiting_seat: null,
        final_revision: { A: 1, B: 1 },
      });
    });
    await screen.findByTestId("duel-outcome");

    // Restart: a brand-new socket replaces the finished one.
    fireEvent.click(screen.getByRole("button", { name: "Restart duel" }));
    expect(factory.instances.length).toBe(2);
    expect(first.closeCalls).toBe(1);
    const second = factory.instances[1];

    // A late frame fired on the OLD socket must not drive the fresh client.
    act(() => {
      first.fireMessage({ ...stateFrame("A", 777), score: 123456 });
    });
    // The fresh room is still connecting (no board yet); the stale frame did
    // not render a board nor leak numbers.
    expect(screen.queryByTestId("duel-score-own")).not.toBeInTheDocument();

    // Driving the NEW socket works normally.
    act(() => {
      second.fireOpen();
      second.fireMessage(welcomeFrame("A", "playing"));
      second.fireMessage(stateFrame("A", 1));
      second.fireMessage(stateFrame("B", 1));
    });
    expect(screen.getByTestId("duel-score-own")).toHaveTextContent("Score: 100");
  });
});

describe("DuelView error and start/sync paths", () => {
  afterEach(() => vi.restoreAllMocks());

  it("surfaces an error frame as an alert and emits no action afterwards", () => {
    const factory = makeFactory();
    render(
      <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
    );
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const socket = factory.instances[0];
    act(() => {
      socket.fireOpen();
      socket.fireMessage(errorFrame("room_full"));
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Duel error: room_full");

    // In the error phase (no seat, not playing) a key emits nothing.
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before)).toHaveLength(0);
  });

  it("start/sync: stays in waiting until an authoritative playing frame, then renders both boards", () => {
    const factory = makeFactory();
    render(
      <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
    );
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const socket = factory.instances[0];

    // Welcome into a WAITING room: the waiting notice shows and no board yet.
    act(() => {
      socket.fireOpen();
      socket.fireMessage(welcomeFrame("A", "waiting"));
    });
    expect(screen.getByTestId("duel-waiting")).toBeInTheDocument();
    expect(screen.queryByTestId("duel-panel-own")).not.toBeInTheDocument();

    // No action while waiting even though a seat is assigned.
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before)).toHaveLength(0);

    // The authoritative playing state frame transitions to playing and both
    // boards render.
    act(() => {
      socket.fireMessage(stateFrame("A", 1));
      socket.fireMessage(stateFrame("B", 1));
    });
    expect(screen.queryByTestId("duel-waiting")).not.toBeInTheDocument();
    expect(screen.getByTestId("duel-panel-own")).toBeInTheDocument();
    expect(screen.getByTestId("duel-panel-opponent")).toBeInTheDocument();

    // Now an action is authorized exactly once per key.
    const before2 = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before2)).toHaveLength(1);
  });
});

describe("DuelView mode-switch / unmount cleanup (no leaks, no solo timer/listener during duel)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(api, "createGame").mockResolvedValue(solo());
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("never runs a solo autotick or solo keyboard move while in duel (solo timer/listener torn down)", async () => {
    vi.useFakeTimers();
    const tickSpy = vi.spyOn(api, "tickGame").mockResolvedValue(solo());
    const moveSpy = vi.spyOn(api, "moveGame").mockResolvedValue(solo());

    render(<App />);
    // Let the solo createGame settle so the solo view is fully mounted.
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(screen.getByTestId("score")).toBeInTheDocument();

    // Switch to duel. SoloView unmounts: its autotick timer and keyboard
    // listener are torn down.
    fireEvent.click(screen.getByTestId("mode-duel"));
    expect(screen.getByLabelText("Room name")).toBeInTheDocument();
    expect(screen.queryByTestId("score")).not.toBeInTheDocument();

    const tickCallsAtSwitch = tickSpy.mock.calls.length;

    // Advance well past any solo gravity interval: NO solo autotick fires while
    // in duel (the solo timer was torn down on unmount).
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    expect(tickSpy.mock.calls.length).toBe(tickCallsAtSwitch);

    // A solo-only arrow key dispatches NO solo move while in duel (no stale
    // solo keyboard listener). The duel view is idle (no room), so it sends
    // nothing either.
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    await act(async () => {
      await Promise.resolve();
    });
    expect(moveSpy).not.toHaveBeenCalled();
  });

  it("App solo->duel->solo keeps solo reachable and mounts exactly one view at a time", async () => {
    render(<App />);
    await screen.findByTestId("score");
    // Exactly the solo view.
    expect(screen.queryByLabelText("Room name")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("mode-duel"));
    // Exactly the duel view; solo panel gone.
    expect(screen.getByLabelText("Room name")).toBeInTheDocument();
    expect(screen.queryByTestId("score")).not.toBeInTheDocument();

    fireEvent.click(screen.getByTestId("mode-solo"));
    // Solo reachable again; duel form gone.
    await screen.findByTestId("score");
    expect(screen.queryByLabelText("Room name")).not.toBeInTheDocument();
  });

  it("unmounting the duel view closes ONLY its owned socket and removes its keyboard listener (no further action)", () => {
    const factory = makeFactory();
    const { unmount } = render(
      <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
    );
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const socket = factory.instances[0];
    act(() => {
      socket.fireOpen();
      socket.fireMessage(welcomeFrame("A", "playing"));
      socket.fireMessage(stateFrame("A", 1));
      socket.fireMessage(stateFrame("B", 1));
    });
    expect(factory.instances).toHaveLength(1);
    expect(socket.listenerCount()).toBe(4);

    unmount();
    // The owned socket is closed and its client listeners removed.
    expect(socket.closeCalls).toBe(1);
    expect(socket.listenerCount()).toBe(0);

    // After unmount, a key fires no further action on the (now closed) socket.
    const before = socket.sent.length;
    fireEvent.keyDown(window, { key: "ArrowLeft" });
    expect(actionSends(socket, before)).toHaveLength(0);
  });

  it("restart opens a FRESH socket and closes the finished one (never reuses a finished room)", async () => {
    const factory = makeFactory();
    render(
      <DuelView clientOptions={{ webSocketImpl: factory.Ctor, resolveUrl: () => "ws://x/ws/duel" }} />,
    );
    fireEvent.change(screen.getByLabelText("Room name"), { target: { value: "room-1" } });
    fireEvent.click(screen.getByRole("button", { name: "Create or join" }));
    const first = factory.instances[0];
    act(() => {
      first.fireOpen();
      first.fireMessage(welcomeFrame("A", "playing"));
      first.fireMessage(stateFrame("A", 1));
      first.fireMessage(stateFrame("B", 1));
      first.fireMessage({
        type: "outcome",
        protocol_version: 1,
        room_id: "room-1",
        result: "win",
        winning_seat: "A",
        losing_seat: "B",
        forfeiting_seat: null,
        final_revision: { A: 1, B: 1 },
      });
    });
    await screen.findByTestId("duel-outcome");

    fireEvent.click(screen.getByRole("button", { name: "Restart duel" }));
    expect(factory.instances.length).toBe(2);
    expect(first.closeCalls).toBe(1);
    // The fresh socket is a brand-new instance, not the finished one.
    expect(factory.instances[1]).not.toBe(first);
    expect(factory.instances[1].closeCalls).toBe(0);
  });
});
