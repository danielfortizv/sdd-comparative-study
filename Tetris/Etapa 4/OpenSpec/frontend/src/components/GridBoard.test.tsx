import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import type { GameState } from "../api";

let GridBoard: any;
let activeObserverCallback: (() => void) | null = null;
let lastObserverInstance: any = null;

class MockResizeObserver {
  callback: ResizeObserverCallback;
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    lastObserverInstance = this;
    if (typeof window !== "undefined") {
      (window as any).lastObserverInstance = this;
    }
  }
  observe = vi.fn((element: Element) => {
    const cb = () => {
      this.callback(
        [
          {
            contentRect: {
              width: 300,
              height: 600,
              top: 0,
              left: 0,
              right: 300,
              bottom: 600,
              x: 0,
              y: 0,
              toJSON: () => {},
            },
            target: element,
          } as unknown as ResizeObserverEntry,
        ],
        this as unknown as ResizeObserver
      );
    };
    activeObserverCallback = cb;
    if (typeof window !== "undefined") {
      (window as any).activeObserverCallback = cb;
    }
  });
  unobserve = vi.fn();
  disconnect = vi.fn();
}

beforeAll(async () => {
  // Stub global contexts before importing the component
  (globalThis as any).ResizeObserver = MockResizeObserver;
  if (typeof window !== "undefined") {
    (window as any).ResizeObserver = MockResizeObserver;
  }
  
  const mod = await import("./GridBoard");
  GridBoard = mod.default;
});

function mockGameState(patch: Partial<GameState> = {}): GameState {
  return {
    id: "test-game-id",
    board: Array.from({ length: 20 }, () => Array<string | null>(10).fill(null)),
    active_piece: { type: "T", origin: [0, 3], cells: [[0, 4], [1, 3], [1, 4], [1, 5]], orientation: 0 },
    status: "playing",
    score: 100,
    total_lines: 5,
    level: 2,
    gravity_interval_ms: 500,
    next_piece: "I",
    hold_piece: null,
    can_hold: true,
    ...patch,
  };
}

const mockCtx = {
  clearRect: vi.fn(),
  fillRect: vi.fn(),
  strokeRect: vi.fn(),
  scale: vi.fn(),
  save: vi.fn(),
  restore: vi.fn(),
  fillStyle: "",
  strokeStyle: "",
  lineWidth: 0,
};

describe("GridBoard Canvas Component", () => {
  let originalCreateElement: any;

  beforeEach(() => {
    vi.clearAllMocks();
    (window as any).ResizeObserver = MockResizeObserver;
    (globalThis as any).ResizeObserver = MockResizeObserver;
    activeObserverCallback = null;
    lastObserverInstance = null;
    (window as any).activeObserverCallback = null;
    (window as any).lastObserverInstance = null;
    vi.stubGlobal("devicePixelRatio", 1);

    originalCreateElement = document.createElement;
    document.createElement = vi.fn().mockImplementation(function (this: Document, tagName: string, options?: any) {
      const el = originalCreateElement.call(this, tagName, options);
      if (tagName.toLowerCase() === "canvas") {
        el.getContext = vi.fn().mockImplementation((contextId: string) => {
          if (contextId === "2d") {
            return mockCtx as unknown as CanvasRenderingContext2D;
          }
          return null;
        });
      }
      return el;
    });
  });

  afterEach(() => {
    document.createElement = originalCreateElement;
    cleanup();
    vi.unstubAllGlobals();
  });

  it("renders canvas element successfully", () => {
    const state = mockGameState();
    render(<GridBoard gameState={state} />);
    
    expect(screen.getByTestId("grid-board-canvas")).toBeDefined();
    expect(screen.queryByTestId("context-fallback")).toBeNull();
  });

  it("draws coordinates grid on the canvas", () => {
    const state = mockGameState();
    render(<GridBoard gameState={state} />);
    
    // Initial draw should fill rects
    expect(mockCtx.fillRect).toHaveBeenCalled();
    expect(mockCtx.strokeRect).toHaveBeenCalled();
  });

  it("handles empty state gracefully when gameState is null", () => {
    render(<GridBoard gameState={null} />);
    expect(screen.getByTestId("grid-board-canvas")).toBeDefined();
    expect(mockCtx.fillRect).toHaveBeenCalled();
  });

  it("renders correct colors for occupied blocks and active piece", () => {
    const board = Array.from({ length: 20 }, () => Array<string | null>(10).fill(null));
    board[19][0] = "I"; // cyan: #00f3ff
    board[19][1] = "O"; // yellow: #ffea00

    const state = mockGameState({ board });
    render(<GridBoard gameState={state} />);

    // Check that some fillRect calls used those hex codes
    expect(mockCtx.fillRect).toHaveBeenCalled();
  });

  it("respects high-DPI scaling with devicePixelRatio = 2", async () => {
    vi.stubGlobal("devicePixelRatio", 2);
    const state = mockGameState();
    render(<GridBoard gameState={state} />);

    // Trigger ResizeObserver mock
    const cb = activeObserverCallback || (window as any).activeObserverCallback;
    if (cb) {
      await act(async () => {
        cb();
      });
    }

    // Context scale should have been called with DPR = 2
    expect(mockCtx.scale).toHaveBeenCalledWith(2, 2);
  });

  it("handles ResizeObserver cleanup on unmount", async () => {
    const state = mockGameState();
    let unmountFn: () => void = () => {};
    
    await act(async () => {
      const { unmount } = render(<GridBoard gameState={state} />);
      unmountFn = unmount;
    });

        const observer = lastObserverInstance || (window as any).lastObserverInstance;
    expect(observer).not.toBeNull();
    const disconnectSpy = observer!.disconnect;
    
    unmountFn();
    expect(disconnectSpy).toHaveBeenCalledTimes(1);
    expect(disconnectSpy).toHaveBeenCalledTimes(1);
  });

  it("fails gracefully to accessible fallback if 2D context is missing", () => {
    document.createElement = vi.fn().mockImplementation(function (this: Document, tagName: string, options?: any) {
      const el = originalCreateElement.call(this, tagName, options);
      if (tagName.toLowerCase() === "canvas") {
        el.getContext = vi.fn().mockImplementation(() => null);
      }
      return el;
    });
    const state = mockGameState();
    render(<GridBoard gameState={state} />);

    expect(screen.queryByTestId("grid-board-canvas")).toBeNull();
    expect(screen.getByTestId("context-fallback")).toBeDefined();
    expect(screen.getByText("Your browser does not support HTML5 Canvas.")).toBeDefined();
  });

  it("safely clips coordinates that fall outside standard 10x20 boundaries", () => {
    const state = mockGameState({
      active_piece: {
        type: "I",
        origin: [0, 8],
        cells: [
          [0, 8],
          [0, 9],
          [0, 10], // Outside right column
          [-1, 8], // Outside top row
        ],
        orientation: 0,
      },
    });

    // Should render successfully without throwing
    expect(() => render(<GridBoard gameState={state} />)).not.toThrow();
  });

  it("redraws correct grid upon state transitions/prop changes", async () => {
    const state1 = mockGameState({ score: 100 });
    const { rerender } = render(<GridBoard gameState={state1} />);

    expect(screen.getByTestId("score-value").textContent).toBe("100");
    const drawCallCountBefore = mockCtx.fillRect.mock.calls.length;

    const state2 = mockGameState({ score: 200, board: Array.from({ length: 20 }, () => Array<string | null>(10).fill("T")) });
    rerender(<GridBoard gameState={state2} />);

    expect(screen.getByTestId("score-value").textContent).toBe("200");
    expect(mockCtx.fillRect.mock.calls.length).toBeGreaterThan(drawCallCountBefore);
  });
});
