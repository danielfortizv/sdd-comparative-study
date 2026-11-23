// =============================================================================
// Canvas renderer native unit fixtures (Task 7.3, M2).
//
// Covers Requirements 14.1 and 14.2.
//
// -----------------------------------------------------------------------------
// MANDATORY SCOPE / EVIDENCE DISCLAIMER (read before trusting these tests)
// -----------------------------------------------------------------------------
// These tests are BEHAVIORAL COVERAGE ONLY. They record the sequence of Canvas
// 2D drawing CALLS issued by the renderer against a MOCK CanvasRenderingContext2D
// whose methods are vitest spies, and they assert React render behavior.
//
// The draw-call records asserted here (counts of fillRect, the arguments to
// setTransform / clearRect / scale, the assigned fillStyle values) and ANY DOM
// attributes on the <canvas> element (role, aria-label, style) are NOT PIXEL
// EVIDENCE and NOT LAYOUT PROOF. A spy recording that `fillRect` was called with
// some coordinates does not prove that any pixel of any color was actually
// painted at any screen position, nor that the board fits a viewport without
// clipping or overlap.
//
// Actual pixel/layout proof is captured INDEPENDENTLY from the UNMODIFIED
// production bundle (Playwright pixel masks / screenshots and the isolated
// own-engine clear fixture) under Task 8.3 and by the independent researcher,
// AFTER this milestone closes. Nothing in this file may be cited as pixel or
// layout evidence.
//
// These tests also deliberately install a controllable mock ResizeObserver and
// a mock 2D context. jsdom provides neither a real 2D rasterizer (getContext
// returns null) nor a ResizeObserver, so the production component is exercised
// against test doubles. That is sufficient to assert the renderer's CALL
// behavior but, again, proves nothing about rendered pixels.
// =============================================================================

import { render } from "@testing-library/react";
import {
  afterEach,
  beforeEach,
  describe,
  expect,
  it,
  vi,
  type MockInstance,
} from "vitest";

import { CanvasBoard, draw } from "./CanvasBoard";
import type { GameState } from "./types";

const ROWS = 20;
const COLS = 10;
const SETTLED_CELLS = ROWS * COLS; // 200

// -----------------------------------------------------------------------------
// Fake 2D context: every method/property the renderer touches is a spy.
// -----------------------------------------------------------------------------
interface FakeContext {
  setTransform: MockInstance;
  clearRect: MockInstance;
  scale: MockInstance;
  fillRect: MockInstance;
  // fillStyle is a real accessor so the renderer can set it; every assignment
  // is recorded in `fillStyleLog` so tests can inspect the color sequence.
  fillStyle: string;
  fillStyleLog: string[];
}

function makeFakeContext(): FakeContext {
  const fillStyleLog: string[] = [];
  const ctx = {
    setTransform: vi.fn(),
    clearRect: vi.fn(),
    scale: vi.fn(),
    fillRect: vi.fn(),
    fillStyleLog,
    _fillStyle: "",
  } as unknown as FakeContext & { _fillStyle: string };

  Object.defineProperty(ctx, "fillStyle", {
    get() {
      return (this as { _fillStyle: string })._fillStyle;
    },
    set(value: string) {
      (this as { _fillStyle: string })._fillStyle = value;
      fillStyleLog.push(value);
    },
    configurable: true,
    enumerable: true,
  });

  return ctx as FakeContext;
}

// -----------------------------------------------------------------------------
// Controllable mock ResizeObserver. jsdom has no ResizeObserver, so we install
// our own double and keep a registry of live instances so a test can drive a
// resize notification and assert disconnect-on-unmount.
// -----------------------------------------------------------------------------
interface MockResizeObserverInstance {
  callback: ResizeObserverCallback;
  observed: Element[];
  disconnected: boolean;
  // Fire a content-box resize notification for the first observed element.
  fire(width: number, height: number): void;
}

const liveObservers: MockResizeObserverInstance[] = [];

class MockResizeObserver implements MockResizeObserverInstance {
  callback: ResizeObserverCallback;
  observed: Element[] = [];
  disconnected = false;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    liveObservers.push(this);
  }

  observe(target: Element): void {
    this.observed.push(target);
  }

  unobserve(target: Element): void {
    this.observed = this.observed.filter((el) => el !== target);
  }

  disconnect(): void {
    this.disconnected = true;
    this.observed = [];
  }

  fire(width: number, height: number): void {
    const entry = {
      contentRect: { width, height } as DOMRectReadOnly,
    } as ResizeObserverEntry;
    this.callback([entry], this as unknown as ResizeObserver);
  }
}

// -----------------------------------------------------------------------------
// State fixtures.
// -----------------------------------------------------------------------------
function emptyBoard(): number[][] {
  return Array.from({ length: ROWS }, () =>
    Array.from({ length: COLS }, () => 0),
  );
}

// Playing state with an O piece (4 on-board overlay cells) and no settled
// blocks: a known fixture whose expected fill count is 200 + 4 = 204.
function oPieceState(): GameState {
  return {
    id: "g",
    status: "playing",
    board: emptyBoard(),
    active_piece: {
      type: "O",
      origin: [0, 0],
      cells: [
        [0, 0],
        [0, 1],
        [1, 0],
        [1, 1],
      ],
    },
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
  };
}

// Settled-only state (no active piece). Expected fill count is exactly 200.
function settledOnlyState(): GameState {
  const state = oPieceState();
  state.active_piece = null;
  state.board[19][0] = 1;
  return state;
}

// =============================================================================
// Pure `draw` helper: draw-call contract.
// =============================================================================
describe("draw (pure renderer helper)", () => {
  it("resets the transform to identity and clears the whole backing store before drawing", () => {
    const ctx = makeFakeContext();
    const cssW = 240;
    const cssH = 480;
    const dpr = 2;

    draw(ctx as unknown as CanvasRenderingContext2D, oPieceState(), cssW, cssH, dpr);

    // Identity transform reset exactly once.
    expect(ctx.setTransform).toHaveBeenCalledTimes(1);
    expect(ctx.setTransform).toHaveBeenCalledWith(1, 0, 0, 1, 0, 0);

    // Clear covers the entire backing store (css * dpr), exactly once.
    expect(ctx.clearRect).toHaveBeenCalledTimes(1);
    expect(ctx.clearRect).toHaveBeenCalledWith(0, 0, cssW * dpr, cssH * dpr);

    // The clear and transform reset must come BEFORE any fill, proving no
    // residual pixels / compounding scale.
    const clearOrder = ctx.clearRect.mock.invocationCallOrder[0];
    const setTransformOrder = ctx.setTransform.mock.invocationCallOrder[0];
    const firstFillOrder = ctx.fillRect.mock.invocationCallOrder[0];
    expect(setTransformOrder).toBeLessThan(firstFillOrder);
    expect(clearOrder).toBeLessThan(firstFillOrder);
  });

  it("applies the DPR scale once", () => {
    const ctx = makeFakeContext();
    const dpr = 2;

    draw(ctx as unknown as CanvasRenderingContext2D, oPieceState(), 240, 480, dpr);

    expect(ctx.scale).toHaveBeenCalledTimes(1);
    expect(ctx.scale).toHaveBeenCalledWith(dpr, dpr);
  });

  it("fills exactly the 200 settled cells plus the active-piece overlay cells", () => {
    const ctx = makeFakeContext();

    // O piece has 4 on-board cells -> 200 + 4 = 204 fills.
    draw(ctx as unknown as CanvasRenderingContext2D, oPieceState(), 240, 480, 1);

    expect(ctx.fillRect).toHaveBeenCalledTimes(SETTLED_CELLS + 4);
  });

  it("fills exactly the 200 settled cells and no overlay when there is no active piece", () => {
    const ctx = makeFakeContext();

    draw(ctx as unknown as CanvasRenderingContext2D, settledOnlyState(), 240, 480, 1);

    expect(ctx.fillRect).toHaveBeenCalledTimes(SETTLED_CELLS);
  });

  it("draws the active-piece overlay at the expected cell coordinates in the type color", () => {
    const ctx = makeFakeContext();
    const cssW = 240;
    const cssH = 480;
    const cellW = cssW / COLS; // 24
    const cellH = cssH / ROWS; // 24

    draw(ctx as unknown as CanvasRenderingContext2D, oPieceState(), cssW, cssH, 1);

    // The last four fillRect calls are the O-piece overlay (cells [0,0] [0,1]
    // [1,0] [1,1]) in the O type color (#facc15, code 2).
    const calls = ctx.fillRect.mock.calls;
    const overlayCalls = calls.slice(SETTLED_CELLS);
    expect(overlayCalls).toEqual([
      [0 * cellW, 0 * cellH, cellW, cellH],
      [1 * cellW, 0 * cellH, cellW, cellH],
      [0 * cellW, 1 * cellH, cellW, cellH],
      [1 * cellW, 1 * cellH, cellW, cellH],
    ]);

    // The fillStyle assigned immediately before the overlay was the O color.
    expect(ctx.fillStyleLog).toContain("#facc15");
  });

  it("skips overlay cells that fall outside the board bounds", () => {
    const ctx = makeFakeContext();
    const state = oPieceState();
    // Two of four cells are off-board (negative row / overflow column).
    state.active_piece = {
      type: "T",
      origin: [-1, 0],
      cells: [
        [-1, 0],
        [0, 0],
        [0, 1],
        [0, 10],
      ],
    };

    draw(ctx as unknown as CanvasRenderingContext2D, state, 240, 480, 1);

    // 200 settled + only the 2 in-bounds overlay cells.
    expect(ctx.fillRect).toHaveBeenCalledTimes(SETTLED_CELLS + 2);
  });
});

// =============================================================================
// CanvasBoard component: context acquisition, absent-context safety,
// ResizeObserver behavior, and unmount cleanup.
// =============================================================================
describe("CanvasBoard component", () => {
  let getContextSpy: MockInstance;
  let fakeCtx: FakeContext | null;
  const originalResizeObserver = globalThis.ResizeObserver;
  const originalDpr = window.devicePixelRatio;

  beforeEach(() => {
    liveObservers.length = 0;
    fakeCtx = makeFakeContext();

    // Return our fake 2D context from getContext("2d"); return null otherwise.
    getContextSpy = vi
      .spyOn(HTMLCanvasElement.prototype, "getContext")
      .mockImplementation((contextId: string) =>
        contextId === "2d" ? (fakeCtx as unknown as CanvasRenderingContext2D) : null,
      );

    // Deterministic, meaningful getBoundingClientRect so the initial draw has a
    // non-zero CSS box.
    vi.spyOn(HTMLCanvasElement.prototype, "getBoundingClientRect").mockReturnValue({
      width: 240,
      height: 480,
      top: 0,
      left: 0,
      right: 240,
      bottom: 480,
      x: 0,
      y: 0,
      toJSON: () => ({}),
    } as DOMRect);

    // Install the controllable mock ResizeObserver and a fixed DPR.
    (globalThis as unknown as { ResizeObserver: typeof MockResizeObserver }).ResizeObserver =
      MockResizeObserver;
    Object.defineProperty(window, "devicePixelRatio", {
      value: 2,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    (globalThis as unknown as { ResizeObserver: typeof originalResizeObserver }).ResizeObserver =
      originalResizeObserver;
    Object.defineProperty(window, "devicePixelRatio", {
      value: originalDpr,
      configurable: true,
    });
  });

  it("acquires the 2D context and draws once on mount, applying the device-pixel-ratio scale", () => {
    render(<CanvasBoard state={oPieceState()} />);

    expect(getContextSpy).toHaveBeenCalledWith("2d");
    // One draw on mount: single transform reset + clear.
    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(1);
    expect(fakeCtx!.clearRect).toHaveBeenCalledTimes(1);
    // DPR 2 scale applied.
    expect(fakeCtx!.scale).toHaveBeenCalledWith(2, 2);
    // 200 settled + 4 O-piece overlay.
    expect(fakeCtx!.fillRect).toHaveBeenCalledTimes(SETTLED_CELLS + 4);
  });

  it("sizes the backing store from the measured CSS box and DPR", () => {
    render(<CanvasBoard state={oPieceState()} />);

    const canvas = document.querySelector("canvas") as HTMLCanvasElement;
    // 240 css * 2 dpr = 480; 480 css * 2 dpr = 960.
    expect(canvas.width).toBe(480);
    expect(canvas.height).toBe(960);
    // The clear covered the whole backing store.
    expect(fakeCtx!.clearRect).toHaveBeenCalledWith(0, 0, 480, 960);
  });

  it("redraws exactly once per authoritative state change", () => {
    const { rerender } = render(<CanvasBoard state={oPieceState()} />);
    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(1);

    // A new authoritative state object (e.g. after a rotation) triggers one
    // more redraw.
    const next = oPieceState();
    next.active_piece = {
      type: "O",
      origin: [0, 1],
      cells: [
        [0, 1],
        [0, 2],
        [1, 1],
        [1, 2],
      ],
    };
    rerender(<CanvasBoard state={next} />);

    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(2);
    expect(fakeCtx!.clearRect).toHaveBeenCalledTimes(2);
  });

  it("renders without throwing and issues no draw calls when the 2D context is absent", () => {
    // getContext("2d") now returns null.
    getContextSpy.mockImplementation(() => null);
    const nullCtxProbe = makeFakeContext();
    fakeCtx = nullCtxProbe; // detached: never returned, so must stay untouched.

    expect(() => render(<CanvasBoard state={oPieceState()} />)).not.toThrow();

    // The canvas element still rendered.
    expect(document.querySelector("canvas")).not.toBeNull();
    // No draw calls on the probe context.
    expect(nullCtxProbe.setTransform).not.toHaveBeenCalled();
    expect(nullCtxProbe.clearRect).not.toHaveBeenCalled();
    expect(nullCtxProbe.fillRect).not.toHaveBeenCalled();
  });

  it("redraws on a meaningful content-box resize", () => {
    render(<CanvasBoard state={oPieceState()} />);
    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(1);

    expect(liveObservers.length).toBe(1);
    const observer = liveObservers[0];

    // A changed measurement (240x480 -> 300x600) is a meaningful resize.
    observer.fire(300, 600);

    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(2);
    expect(fakeCtx!.clearRect).toHaveBeenCalledTimes(2);
    // Backing store recomputed: 300 * 2 = 600, 600 * 2 = 1200.
    expect(fakeCtx!.clearRect).toHaveBeenLastCalledWith(0, 0, 600, 1200);
  });

  it("does not force a resize-driven redraw on an unchanged measurement", () => {
    render(<CanvasBoard state={oPieceState()} />);
    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(1);

    const observer = liveObservers[0];
    // Same measurement as the initial getBoundingClientRect (240x480): no
    // meaningful resize, so no additional redraw.
    observer.fire(240, 480);

    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(1);
    expect(fakeCtx!.clearRect).toHaveBeenCalledTimes(1);
  });

  it("disconnects the observer on unmount and fires no draw after unmount", () => {
    const { unmount } = render(<CanvasBoard state={oPieceState()} />);
    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(1);

    const observer = liveObservers[0];
    expect(observer.disconnected).toBe(false);

    unmount();

    // The observer was disconnected on unmount.
    expect(observer.disconnected).toBe(true);

    // Even if a stray callback fires after unmount, no draw occurs.
    const callsBefore = fakeCtx!.setTransform.mock.calls.length;
    observer.fire(999, 999);
    expect(fakeCtx!.setTransform.mock.calls.length).toBe(callsBefore);
  });

  it("still draws from state and does not throw when ResizeObserver is undefined", () => {
    (globalThis as unknown as { ResizeObserver: undefined }).ResizeObserver =
      undefined as unknown as undefined;

    expect(() => render(<CanvasBoard state={oPieceState()} />)).not.toThrow();

    // The state-keyed draw still ran even with no ResizeObserver.
    expect(fakeCtx!.setTransform).toHaveBeenCalledTimes(1);
    expect(fakeCtx!.fillRect).toHaveBeenCalledTimes(SETTLED_CELLS + 4);
    // No observer was constructed.
    expect(liveObservers.length).toBe(0);
  });
});
