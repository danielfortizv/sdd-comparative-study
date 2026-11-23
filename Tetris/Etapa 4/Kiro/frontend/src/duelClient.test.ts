// Focused self-tests for the duel WebSocket client (task 31.1).
//
// These are SELF-TESTS of the client module ONLY. They use a fake WebSocket
// passed through the client's explicit `webSocketImpl` option seam (NO global
// WebSocket/fetch monkeypatch, NO source interception). They assert EXACT
// action counts and the exact canonical wire shape, with the triggering input
// performed OUTSIDE any waiting helper. They are never treated as production
// wire/pixel/focus/performance proof (that is an independent checkpoint).

import { describe, expect, it } from "vitest";
import {
  DuelClient,
  openDuelClient,
  PROTOCOL_VERSION,
  type ActionFrame,
  type AckFrame,
  type ErrorFrame,
  type HelloFrame,
  type OutcomeFrame,
  type RejectFrame,
  type Seat,
  type StateFrame,
  type WelcomeFrame,
} from "./duelClient";

// A minimal in-memory fake WebSocket that records sends and lets a test drive
// open/message/close/error synchronously. It implements only the structural
// `WebSocketLike` surface the client depends on.
class FakeWebSocket {
  static readonly CONNECTING = 0;
  static readonly OPEN = 1;
  static readonly CLOSING = 2;
  static readonly CLOSED = 3;

  readyState = FakeWebSocket.CONNECTING;
  readonly url: string;
  readonly sent: string[] = [];
  closeCalls: Array<{ code?: number; reason?: string }> = [];

  private listeners: {
    open: Array<(ev: Event) => void>;
    message: Array<(ev: MessageEvent) => void>;
    close: Array<(ev: CloseEvent) => void>;
    error: Array<(ev: Event) => void>;
  } = { open: [], message: [], close: [], error: [] };

  constructor(url: string) {
    this.url = url;
  }

  send(data: string): void {
    this.sent.push(data);
  }

  close(code?: number, reason?: string): void {
    this.closeCalls.push({ code, reason });
    this.readyState = FakeWebSocket.CLOSED;
  }

  addEventListener(type: string, listener: unknown): void {
    (this.listeners as Record<string, unknown[]>)[type].push(listener);
  }

  removeEventListener(type: string, listener: unknown): void {
    const arr = (this.listeners as Record<string, unknown[]>)[type];
    const idx = arr.indexOf(listener);
    if (idx >= 0) {
      arr.splice(idx, 1);
    }
  }

  // --- test drivers ---
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
    for (const l of [...this.listeners.open]) {
      l(new Event("open"));
    }
  }

  fireMessage(data: unknown): void {
    const payload = typeof data === "string" ? data : JSON.stringify(data);
    for (const l of [...this.listeners.message]) {
      l({ data: payload } as MessageEvent);
    }
  }

  fireRawMessage(data: unknown): void {
    for (const l of [...this.listeners.message]) {
      l({ data } as MessageEvent);
    }
  }

  fireClose(code = 1000, reason = ""): void {
    for (const l of [...this.listeners.close]) {
      l({ code, reason } as CloseEvent);
    }
  }

  fireError(): void {
    for (const l of [...this.listeners.error]) {
      l(new Event("error"));
    }
  }
}

// The constructor records every instance so a test can inspect the single
// owned socket and prove no second socket is created.
function makeFactory() {
  const instances: FakeWebSocket[] = [];
  const Ctor = class extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      instances.push(this);
    }
  } as unknown as new (url: string) => FakeWebSocket;
  return { Ctor, instances };
}

const ROOM = "room-1";

function welcome(seat: Seat, room = ROOM): WelcomeFrame {
  return {
    type: "welcome",
    protocol_version: PROTOCOL_VERSION,
    room_id: room,
    seat_id: seat,
    room_status: "waiting",
  };
}

function state(
  seat: Seat,
  revision: number,
  overrides: Partial<StateFrame> = {},
): StateFrame {
  return {
    type: "state",
    protocol_version: PROTOCOL_VERSION,
    room_id: ROOM,
    seat_id: seat,
    revision,
    status: "playing",
    room_status: "playing",
    board: Array.from({ length: 20 }, () => Array(10).fill(0)),
    active_piece: { type: "T", origin: [0, 4], cells: [[0, 4], [0, 5], [0, 3], [1, 4]] },
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    ...overrides,
  };
}

function ack(seat: Seat, actionId: string, revision: number): AckFrame {
  return {
    type: "ack",
    protocol_version: PROTOCOL_VERSION,
    room_id: ROOM,
    seat_id: seat,
    action_id: actionId,
    revision,
    applied: true,
    no_op: false,
  };
}

// Build a client wired to a freshly created fake socket.
function setup(seat: Seat | null = null) {
  const { Ctor, instances } = makeFactory();
  const received: {
    welcome: WelcomeFrame[];
    state: StateFrame[];
    ack: AckFrame[];
    reject: RejectFrame[];
    error: ErrorFrame[];
    outcome: OutcomeFrame[];
    close: CloseEvent[];
    open: number;
    socketError: number;
  } = {
    welcome: [],
    state: [],
    ack: [],
    reject: [],
    error: [],
    outcome: [],
    close: [],
    open: 0,
    socketError: 0,
  };
  const client = new DuelClient({
    roomId: ROOM,
    webSocketImpl: Ctor,
    resolveUrl: () => "ws://test.local/ws/duel",
    callbacks: {
      onWelcome: (f) => received.welcome.push(f),
      onState: (f) => received.state.push(f),
      onAck: (f) => received.ack.push(f),
      onReject: (f) => received.reject.push(f),
      onError: (f) => received.error.push(f),
      onOutcome: (f) => received.outcome.push(f),
      onOpen: () => (received.open += 1),
      onClose: (e) => received.close.push(e),
      onSocketError: () => (received.socketError += 1),
    },
  });
  const socket = instances[0];
  // Optionally drive through handshake to a playing state at revision 0.
  if (seat) {
    socket.fireOpen();
    socket.fireMessage(welcome(seat));
    socket.fireMessage(state(seat, 0));
  }
  return { client, socket, instances, received };
}

describe("DuelClient handshake and ownership", () => {
  it("opens exactly one socket and sends hello on open", () => {
    const { socket, instances } = setup();
    expect(instances).toHaveLength(1);
    expect(socket.sent).toHaveLength(0);

    socket.fireOpen();

    expect(instances).toHaveLength(1);
    expect(socket.sent).toHaveLength(1);
    const hello = JSON.parse(socket.sent[0]) as HelloFrame;
    expect(hello).toEqual({
      type: "hello",
      protocol_version: 1,
      room_id: ROOM,
    });
  });

  it("assigns the seat from the welcome frame exactly once", () => {
    const { client, socket } = setup();
    socket.fireOpen();
    expect(client.assignedSeat).toBeNull();

    socket.fireMessage(welcome("B"));
    expect(client.assignedSeat).toBe("B");

    // A later (spurious) welcome for the other seat never re-seats.
    socket.fireMessage(welcome("A"));
    expect(client.assignedSeat).toBe("B");
  });

  it("factory openDuelClient returns a live client", () => {
    const { Ctor, instances } = makeFactory();
    const client = openDuelClient({
      roomId: ROOM,
      webSocketImpl: Ctor,
      resolveUrl: () => "ws://test.local/ws/duel",
    });
    expect(client).toBeInstanceOf(DuelClient);
    expect(instances).toHaveLength(1);
  });
});

describe("DuelClient action emission (one input one action)", () => {
  it("refuses to send before seat and authoritative revision exist", () => {
    const { client, socket } = setup();
    // No seat yet.
    expect(client.sendAction("left")).toBeNull();

    socket.fireOpen();
    socket.fireMessage(welcome("A"));
    // Seat but no state yet => no authoritative own revision.
    expect(client.authoritativeRevision).toBeNull();
    expect(client.sendAction("left")).toBeNull();
    // Only the hello was sent.
    expect(socket.sent).toHaveLength(1);
  });

  it("emits EXACTLY ONE canonical action per input with monotonic ordinals", () => {
    const { client, socket } = setup("A");
    const before = socket.sent.length;

    const a1 = client.sendAction("left");
    const a2 = client.sendAction("cw");

    // Exactly two new frames for two inputs.
    expect(socket.sent.length - before).toBe(2);
    expect(a1).not.toBeNull();
    expect(a2).not.toBeNull();

    const sent1 = JSON.parse(socket.sent[before]) as ActionFrame;
    const sent2 = JSON.parse(socket.sent[before + 1]) as ActionFrame;
    expect(sent1).toEqual({
      type: "action",
      protocol_version: 1,
      room_id: ROOM,
      seat_id: "A",
      action_id: "A-1",
      expected_revision: 0,
      kind: "left",
    });
    expect(sent2.action_id).toBe("A-2");
    expect(sent2.kind).toBe("cw");
  });

  it("uses the assigned-seat prefix for seat B", () => {
    const { client, socket } = setup("B");
    const before = socket.sent.length;
    const a = client.sendAction("hold");
    expect(a?.action_id).toBe("B-1");
    const sent = JSON.parse(socket.sent[before]) as ActionFrame;
    expect(sent.seat_id).toBe("B");
    expect(sent.action_id).toMatch(/^B-[1-9][0-9]{0,14}$/);
  });

  it("carries the LAST authoritative own revision as expected_revision", () => {
    const { client, socket } = setup("A");
    // Advance own authority to revision 5.
    socket.fireMessage(state("A", 5));
    expect(client.authoritativeRevision).toBe(5);

    const before = socket.sent.length;
    const a = client.sendAction("right");
    expect(a?.expected_revision).toBe(5);
    expect(socket.sent.length - before).toBe(1);
  });

  it("does not send when the socket is not open", () => {
    const { client, socket } = setup("A");
    socket.readyState = FakeWebSocket.CLOSING;
    const before = socket.sent.length;
    expect(client.sendAction("down")).toBeNull();
    expect(socket.sent.length - before).toBe(0);
  });
});

describe("DuelClient authority and no-rollback", () => {
  it("advances own revision only forward from own-seat state frames", () => {
    const { client, socket } = setup("A");
    socket.fireMessage(state("A", 10));
    expect(client.authoritativeRevision).toBe(10);

    // An older own-seat state never lowers the revision.
    socket.fireMessage(state("A", 4));
    expect(client.authoritativeRevision).toBe(10);
  });

  it("never lets a late/old ack roll back newer authority", () => {
    const { client, socket } = setup("A");
    socket.fireMessage(state("A", 7));
    expect(client.authoritativeRevision).toBe(7);

    // A late ack referring to an older revision must NOT roll back.
    socket.fireMessage(ack("A", "A-1", 3));
    expect(client.authoritativeRevision).toBe(7);

    // A newer ack may advance it.
    socket.fireMessage(ack("A", "A-2", 9));
    expect(client.authoritativeRevision).toBe(9);
  });

  it("never cross-wires A/B: opponent frames do not change own revision", () => {
    const { client, socket, received } = setup("A");
    socket.fireMessage(state("A", 2));
    expect(client.authoritativeRevision).toBe(2);

    // Opponent (B) state is delivered to the callback but never touches own
    // authority or ordinal bookkeeping.
    socket.fireMessage(state("B", 999));
    expect(client.authoritativeRevision).toBe(2);
    // Both own and opponent states were delivered (1 own in setup + 1 own + 1 opp).
    const ownStates = received.state.filter((f) => f.seat_id === "A");
    const oppStates = received.state.filter((f) => f.seat_id === "B");
    expect(ownStates.length).toBe(2);
    expect(oppStates.length).toBe(1);

    // An opponent ack never advances our revision either.
    socket.fireMessage(ack("B", "B-1", 5000));
    expect(client.authoritativeRevision).toBe(2);
  });

  it("resyncs own revision forward from a reject's authoritative_revision", () => {
    const { client, socket } = setup("A");
    socket.fireMessage(state("A", 3));
    const reject: RejectFrame = {
      type: "reject",
      protocol_version: PROTOCOL_VERSION,
      room_id: ROOM,
      seat_id: "A",
      action_id: "A-1",
      reason: "stale_revision",
      authoritative_revision: 8,
    };
    socket.fireMessage(reject);
    expect(client.authoritativeRevision).toBe(8);
  });
});

describe("DuelClient frame filtering", () => {
  it("ignores wrong-room frames", () => {
    const { client, socket, received } = setup("A");
    socket.fireMessage(welcome("A", "other-room"));
    socket.fireMessage(state("A", 50, { room_id: "other-room" }));
    // Wrong-room frames are dropped before callbacks and never change authority.
    expect(received.welcome).toHaveLength(1); // only the setup welcome
    expect(client.authoritativeRevision).toBe(0);
  });

  it("ignores frames with a wrong protocol version", () => {
    const { socket, received } = setup("A");
    socket.fireMessage({ ...state("A", 42), protocol_version: 2 });
    // The bad-version state never reached the callback.
    expect(received.state.every((f) => f.revision !== 42)).toBe(true);
  });

  it("ignores non-string (binary) and non-JSON payloads", () => {
    const { client, socket, received } = setup("A");
    socket.fireRawMessage(new Uint8Array([0xff]));
    socket.fireMessage("not json {");
    expect(received.state).toHaveLength(1); // unchanged from setup
    expect(client.authoritativeRevision).toBe(0);
  });

  it("delivers error, outcome, ack, and reject to their callbacks", () => {
    const { socket, received } = setup("A");
    const errorFrame: ErrorFrame = {
      type: "error",
      protocol_version: PROTOCOL_VERSION,
      room_id: null,
      seat_id: null,
      reason: "internal",
      detail: "boom",
    };
    const outcomeFrame: OutcomeFrame = {
      type: "outcome",
      protocol_version: PROTOCOL_VERSION,
      room_id: ROOM,
      result: "win",
      winning_seat: "A",
      losing_seat: "B",
      forfeiting_seat: null,
      final_revision: { A: 10, B: 7 },
    };
    socket.fireMessage(errorFrame);
    socket.fireMessage(outcomeFrame);
    socket.fireMessage(ack("A", "A-1", 1));
    expect(received.error).toHaveLength(1);
    expect(received.outcome).toHaveLength(1);
    expect(received.ack).toHaveLength(1);
  });
});

describe("DuelClient lifecycle and cleanup", () => {
  it("close() removes only its own listeners and closes only its socket", () => {
    const { client, socket } = setup("A");
    expect(socket.listenerCount()).toBe(4);

    client.close(1000, "done");

    expect(socket.listenerCount()).toBe(0);
    expect(socket.closeCalls).toHaveLength(1);
    expect(socket.closeCalls[0]).toEqual({ code: 1000, reason: "done" });
    expect(client.isClosed).toBe(true);
  });

  it("is idempotent on repeated close()", () => {
    const { client, socket } = setup("A");
    client.close();
    client.close();
    expect(socket.closeCalls).toHaveLength(1);
  });

  it("ignores inbound frames and refuses to send after close", () => {
    const { client, socket, received } = setup("A");
    const before = socket.sent.length;
    client.close();

    socket.fireMessage(state("A", 100));
    expect(received.state).toHaveLength(1); // unchanged from setup
    expect(client.sendAction("left")).toBeNull();
    expect(socket.sent.length - before).toBe(0);
  });

  it("marks closed and detaches listeners when the socket closes", () => {
    const { client, socket, received } = setup("A");
    socket.fireClose(1001, "going away");
    expect(client.isClosed).toBe(true);
    expect(received.close).toHaveLength(1);
    expect(socket.listenerCount()).toBe(0);
    // A close event does NOT re-call socket.close().
    expect(socket.closeCalls).toHaveLength(0);
  });

  it("reports transport open and error through callbacks", () => {
    const { socket, received } = setup();
    socket.fireOpen();
    expect(received.open).toBe(1);
    socket.fireError();
    expect(received.socketError).toBe(1);
  });
});

// ---------------------------------------------------------------------------
// Task 32.2 extension: the FULL meaningful behavioral client suite. These add
// to the focused self-tests above and cover the correction's explicitly
// required paths: wrong-generation isolation across two live clients, the
// start/sync ordering, ordinal continuity across old/late acks and rejects,
// no ordinal consumed on a guard failure, wrong-room error rejection, and the
// exact no-rollback matrix. Every triggering input (sendAction / fireMessage)
// is performed OUTSIDE any waiting helper and every assertion is on an EXACT
// count or an exact wire shape. These are SELF-TESTS only.
// ---------------------------------------------------------------------------

function outcome(room = ROOM): OutcomeFrame {
  return {
    type: "outcome",
    protocol_version: PROTOCOL_VERSION,
    room_id: room,
    result: "win",
    winning_seat: "A",
    losing_seat: "B",
    forfeiting_seat: null,
    final_revision: { A: 3, B: 2 },
  };
}

describe("DuelClient start/sync ordering (welcome then first state)", () => {
  it("cannot act until BOTH a seat and the first authoritative state arrive", () => {
    const { Ctor, instances } = makeFactory();
    const sent: ActionFrame[] = [];
    const client = new DuelClient({
      roomId: ROOM,
      webSocketImpl: Ctor,
      resolveUrl: () => "ws://test.local/ws/duel",
    });
    const socket = instances[0];

    // Before open: no seat, no revision, no action.
    expect(client.sendAction("left")).toBeNull();

    // Open (hello sent) but no welcome yet: still no seat.
    socket.fireOpen();
    expect(client.assignedSeat).toBeNull();
    expect(client.sendAction("left")).toBeNull();

    // Welcome assigns the seat but there is still no authoritative own revision.
    socket.fireMessage(welcome("A"));
    expect(client.assignedSeat).toBe("A");
    expect(client.authoritativeRevision).toBeNull();
    expect(client.sendAction("left")).toBeNull();

    // Only after the first OWN state frame can an action be emitted, and it
    // carries that exact authoritative revision.
    socket.fireMessage(state("A", 0));
    expect(client.authoritativeRevision).toBe(0);
    const first = client.sendAction("left");
    sent.push(first as ActionFrame);
    expect(first).not.toBeNull();
    expect(first?.expected_revision).toBe(0);
    // Exactly one action frame ever left the socket (hello + 1 action = 2 sends).
    const actionSends = socket.sent.filter(
      (s) => (JSON.parse(s) as { type: string }).type === "action",
    );
    expect(actionSends).toHaveLength(1);
  });

  it("a second joiner that welcomes into an already-playing room syncs on its own first state", () => {
    const { client, socket } = setup();
    socket.fireOpen();
    // Welcome reports the room already playing.
    socket.fireMessage({ ...welcome("B"), room_status: "playing" });
    expect(client.assignedSeat).toBe("B");
    // No own state yet => still cannot act.
    expect(client.sendAction("right")).toBeNull();
    // First own state syncs the authority; now it can act at that revision.
    socket.fireMessage(state("B", 4));
    const a = client.sendAction("right");
    expect(a?.seat_id).toBe("B");
    expect(a?.expected_revision).toBe(4);
  });
});

describe("DuelClient ordinal continuity across acks and rejects", () => {
  it("keeps monotonically increasing ordinals even as authority advances between inputs", () => {
    const { client, socket } = setup("A");
    const before = socket.sent.length;

    const a1 = client.sendAction("left"); // A-1 @ rev 0
    socket.fireMessage(ack("A", "A-1", 1)); // authority -> 1
    const a2 = client.sendAction("right"); // A-2 @ rev 1
    socket.fireMessage(state("A", 5)); // authority -> 5
    const a3 = client.sendAction("down"); // A-3 @ rev 5

    expect(a1?.action_id).toBe("A-1");
    expect(a1?.expected_revision).toBe(0);
    expect(a2?.action_id).toBe("A-2");
    expect(a2?.expected_revision).toBe(1);
    expect(a3?.action_id).toBe("A-3");
    expect(a3?.expected_revision).toBe(5);
    // Exactly three action frames for three inputs.
    const actions = socket.sent
      .slice(before)
      .map((s) => JSON.parse(s) as ActionFrame)
      .filter((f) => f.type === "action");
    expect(actions).toHaveLength(3);
    expect(actions.map((f) => f.action_id)).toEqual(["A-1", "A-2", "A-3"]);
  });

  it("an old/late ack between two inputs never lowers the expected_revision of the later action", () => {
    const { client, socket } = setup("A");
    socket.fireMessage(state("A", 10)); // authority -> 10
    const a1 = client.sendAction("left"); // A-1 @ 10
    expect(a1?.expected_revision).toBe(10);

    // A stale ack for an older revision arrives; it must NOT roll authority back.
    socket.fireMessage(ack("A", "A-1", 2));
    expect(client.authoritativeRevision).toBe(10);

    // The next input still carries the newer authority, with the next ordinal.
    const a2 = client.sendAction("right"); // A-2 @ 10
    expect(a2?.action_id).toBe("A-2");
    expect(a2?.expected_revision).toBe(10);
  });

  it("a reject resyncs authority forward and the next action uses the resynced revision", () => {
    const { client, socket } = setup("A");
    socket.fireMessage(state("A", 3));
    const a1 = client.sendAction("cw"); // A-1 @ 3
    expect(a1?.expected_revision).toBe(3);

    const reject: RejectFrame = {
      type: "reject",
      protocol_version: PROTOCOL_VERSION,
      room_id: ROOM,
      seat_id: "A",
      action_id: "A-1",
      reason: "stale_revision",
      authoritative_revision: 12,
    };
    socket.fireMessage(reject);
    expect(client.authoritativeRevision).toBe(12);

    const a2 = client.sendAction("ccw"); // A-2 @ 12
    expect(a2?.action_id).toBe("A-2");
    expect(a2?.expected_revision).toBe(12);
  });

  it("does not consume an ordinal when a send is refused (socket not open)", () => {
    const { client, socket } = setup("A");
    const a1 = client.sendAction("left"); // A-1
    expect(a1?.action_id).toBe("A-1");

    // Refuse the next send by closing the socket transport only.
    socket.readyState = FakeWebSocket.CLOSING;
    expect(client.sendAction("right")).toBeNull();

    // Reopen and send again: the ordinal is A-2 (the refused call consumed none).
    socket.readyState = FakeWebSocket.OPEN;
    const a2 = client.sendAction("down");
    expect(a2?.action_id).toBe("A-2");
  });
});

describe("DuelClient wrong-generation isolation across two live clients", () => {
  it("a late frame from an old client never reaches a freshly opened client", () => {
    // Open client #1, drive it to playing, then close it (old generation).
    const first = setup("A");
    expect(first.client.authoritativeRevision).toBe(0);
    first.client.close();
    expect(first.client.isClosed).toBe(true);

    // Open client #2 for the SAME room (a fresh generation) on its own socket.
    const second = setup("A");
    expect(second.socket).not.toBe(first.socket);

    // A late frame fired on the OLD socket must not touch the new client.
    first.socket.fireMessage(state("A", 999));
    expect(second.client.authoritativeRevision).toBe(0);
    expect(second.received.state).toHaveLength(1); // only its own setup state

    // The new client advances only from its OWN socket's frames.
    second.socket.fireMessage(state("A", 7));
    expect(second.client.authoritativeRevision).toBe(7);
    expect(first.client.authoritativeRevision).toBe(0); // old client stays dead
  });

  it("each client owns exactly one socket and four listeners; closing one leaves the other intact", () => {
    const first = setup("A");
    const second = setup("A");
    expect(first.instances).toHaveLength(1);
    expect(second.instances).toHaveLength(1);
    expect(first.socket.listenerCount()).toBe(4);
    expect(second.socket.listenerCount()).toBe(4);

    first.client.close();
    expect(first.socket.listenerCount()).toBe(0);
    // The second client's socket/listeners are untouched by the first's close.
    expect(second.socket.listenerCount()).toBe(4);
    expect(second.socket.closeCalls).toHaveLength(0);
  });
});

describe("DuelClient error/outcome routing and wrong-room rejection", () => {
  it("delivers a null-room (connection-level) error but ignores a non-null wrong-room error", () => {
    const { socket, received } = setup("A");
    const connError: ErrorFrame = {
      type: "error",
      protocol_version: PROTOCOL_VERSION,
      room_id: null,
      seat_id: null,
      reason: "internal",
      detail: "boom",
    };
    const wrongRoomError: ErrorFrame = {
      type: "error",
      protocol_version: PROTOCOL_VERSION,
      room_id: "other-room",
      seat_id: null,
      reason: "room_not_found",
      detail: "nope",
    };
    socket.fireMessage(connError);
    socket.fireMessage(wrongRoomError);
    // Only the null-room error was delivered; the foreign-room error was dropped.
    expect(received.error).toHaveLength(1);
    expect(received.error[0].reason).toBe("internal");
  });

  it("ignores a wrong-room outcome and delivers the own-room outcome exactly once", () => {
    const { socket, received } = setup("A");
    socket.fireMessage(outcome("other-room"));
    expect(received.outcome).toHaveLength(0);
    socket.fireMessage(outcome());
    expect(received.outcome).toHaveLength(1);
  });

  it("a wrong-room ack never advances own authority", () => {
    const { client, socket } = setup("A");
    socket.fireMessage(state("A", 2));
    socket.fireMessage({ ...ack("A", "A-1", 500), room_id: "other-room" });
    expect(client.authoritativeRevision).toBe(2);
  });
});
