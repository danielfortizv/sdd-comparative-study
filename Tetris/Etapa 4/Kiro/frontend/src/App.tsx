// Application shell: an accessible solo/duel mode switch plus the two views.
//
// The solo view (Stage 2/3) and the duel view (M3) are DISTINCT, independently
// usable views. The shell mounts EXACTLY ONE of them at a time: solo stays
// reachable, and the layout never requires three boards to render at once
// (Req 15.1-15.3).
//
// Lifecycle safety (design.md "Lifecycle safety"): the solo game hook
// (`useGame`) owns the solo autotick timer AND the solo keyboard listener, and
// it lives INSIDE `SoloView`. Because the shell mounts only one view at a time,
// switching to duel UNMOUNTS `SoloView`, which tears down the solo autotick and
// the solo keyboard listener (so there is no hidden solo autotick or solo key
// listener while in duel). Switching back UNMOUNTS `DuelView`, which closes its
// single owned socket (no stale duel socket effect in solo). The duel view owns
// and cleans up only its own socket/listeners/handlers.

import { useCallback, useEffect, useRef, useState } from "react";

import { CanvasBoard } from "./CanvasBoard";
import { DuelView } from "./DuelView";
import { HighScores } from "./HighScores";
import { Preview } from "./Preview";
import { useGame } from "./useGame";
import { useHighScores } from "./useHighScores";

type Mode = "solo" | "duel";

export function App() {
  const [mode, setMode] = useState<Mode>("solo");

  const goSolo = useCallback(() => setMode("solo"), []);
  const goDuel = useCallback(() => setMode("duel"), []);

  return (
    <div
      style={{
        // box-sizing: border-box (from index.css) keeps the 12px padding and
        // the 100vh min-height within the viewport, so the page does not
        // overflow at 1280x900. The shell fills the full viewport width so the
        // wrapping rows below have the real available width to lay out against.
        boxSizing: "border-box",
        minHeight: "100vh",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
        padding: 12,
        fontFamily: "system-ui, sans-serif",
        color: "#e5e7eb",
        background: "#0b1120",
      }}
    >
      <h1 style={{ margin: "4px 0", fontSize: 22 }}>Tetris - Stage 4</h1>

      {/* Accessible mode switch. Solo is always reachable; exactly one view is
          mounted at a time so no hidden solo timer/listener runs during a duel
          and no stale duel socket survives in solo. */}
      <div
        role="tablist"
        aria-label="Game mode"
        style={{ display: "flex", gap: 8 }}
      >
        <button
          type="button"
          role="tab"
          aria-selected={mode === "solo"}
          data-testid="mode-solo"
          onClick={goSolo}
          disabled={mode === "solo"}
        >
          Solo
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "duel"}
          data-testid="mode-duel"
          onClick={goDuel}
          disabled={mode === "duel"}
        >
          Duel
        </button>
      </div>

      {mode === "solo" ? <SoloView /> : <DuelView onExit={goSolo} />}
    </div>
  );
}

// The Stage 2/3 solo single-player view. All solo game state, the automatic
// gravity tick, and the solo keyboard listener live here (via `useGame`), so
// unmounting this component on a mode switch tears every one of them down.
export function SoloView() {
  const { state, error, move, rotate, hold, restart } = useGame();
  const highScores = useHighScores();

  // Restart ownership (Req 8.8, 8.9, 9.4): synchronously invalidate the current
  // leaderboard generation BEFORE creating the new game, so no leaderboard
  // response captured before the restart (delayed fetch or delayed JSON,
  // success or error) can commit over the fresh game. The two calls are
  // independent; this does not touch the game FIFO/timers.
  const handleRestart = useCallback(() => {
    highScores.invalidate();
    return restart();
  }, [highScores, restart]);

  // Fetch the leaderboard again on each real playing -> game_over transition,
  // detected with a ref so it fires once per transition and never on every
  // render or every automatic tick (Req 8.6, 8.7).
  const prevStatusRef = useRef<string | null>(null);
  useEffect(() => {
    const current = state?.status ?? null;
    if (prevStatusRef.current === "playing" && current === "game_over") {
      highScores.refresh();
    }
    prevStatusRef.current = current;
  }, [state?.status, highScores]);

  // Map arrow keys to moves and C/c to Hold while the game is playing.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (state?.status !== "playing") {
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        void move("left");
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        void move("right");
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        void move("down");
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        void rotate("cw");
      } else if (event.key === "z" || event.key === "Z") {
        event.preventDefault();
        void rotate("ccw");
      } else if (event.key === "c" || event.key === "C") {
        event.preventDefault();
        if (state.can_hold) {
          void hold();
        }
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [state, move, rotate, hold]);

  const holdDisabled =
    state?.status !== "playing" || !state.can_hold;

  // Human-readable status text exposed in an accessible DOM region. The game
  // status (playing / game_over) is rendered as TEXT here so it never depends
  // solely on Canvas pixels (Req 12.4). The CanvasBoard surface is visual only.
  const statusText =
    state?.status === "game_over" ? "Game over" : "Playing";

  return (
    <section
      aria-label="Solo"
      style={{
        boxSizing: "border-box",
        width: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
      }}
    >
      {error && <p style={{ color: "#f87171" }}>Error: {error}</p>}

      {state ? (
        <>
          <div
            style={{
              display: "flex",
              gap: 20,
              alignItems: "flex-start",
              // Wrap at narrow widths so the board/status/leaderboard stack
              // instead of overflowing the row and pushing the board off the
              // left edge of the viewport. The row never exceeds viewport width.
              flexWrap: "wrap",
              justifyContent: "center",
              width: "100%",
              maxWidth: 920,
            }}
          >
            {/* Canvas board renderer replaces the per-cell DOM grid. The
                wrapper is ADAPTIVE (not a fixed 240px box): it grows/shrinks
                with the available row width between a readable minimum and a
                desktop cap, so the canvas content-box CSS width actually
                changes on viewport resize. The 10x20 geometry is preserved by
                the canvas aspect-ratio. */}
            <div
              style={{
                flex: "1 1 240px",
                minWidth: 160,
                maxWidth: 320,
              }}
            >
              <CanvasBoard state={state} />
            </div>

            <aside
              aria-label="Game status"
              style={{ display: "flex", flexDirection: "column", gap: 10, minWidth: 140 }}
            >
              {/* Text status region: communicates playing / game_over as text
                  so status never depends solely on Canvas pixels (Req 12.4). */}
              <div
                role="status"
                aria-label="Game status text"
                data-testid="status"
              >
                Status: {statusText}
              </div>

              <div>
                <div data-testid="score">Score: {state.score}</div>
                <div data-testid="lines">Lines: {state.total_lines}</div>
                <div data-testid="level">Level: {state.level}</div>
              </div>

              <div>
                <div style={{ marginBottom: 4 }}>Next</div>
                <Preview piece={state.next_piece} label="Next piece" />
              </div>

              <div>
                <div style={{ marginBottom: 4 }}>Hold</div>
                <Preview piece={state.hold_piece} label="Hold piece" />
                {state.hold_piece === null && (
                  <div style={{ fontSize: 12, opacity: 0.7 }}>Empty</div>
                )}
              </div>
            </aside>

            <HighScores status={highScores.status} entries={highScores.entries} />
          </div>

          {state.status === "game_over" && (
            <p style={{ fontSize: 20, fontWeight: 700, color: "#f87171", margin: "4px 0" }}>
              Game Over
            </p>
          )}

          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={() => void move("left")}
              disabled={state.status !== "playing"}
            >
              Left
            </button>
            <button
              onClick={() => void move("down")}
              disabled={state.status !== "playing"}
            >
              Soft Drop
            </button>
            <button
              onClick={() => void move("right")}
              disabled={state.status !== "playing"}
            >
              Right
            </button>
            <button
              onClick={() => void rotate("cw")}
              disabled={state.status !== "playing"}
              aria-label="Rotate clockwise"
            >
              Rotate CW
            </button>
            <button
              onClick={() => void rotate("ccw")}
              disabled={state.status !== "playing"}
              aria-label="Rotate counter-clockwise"
            >
              Rotate CCW
            </button>
            <button onClick={() => void hold()} disabled={holdDisabled}>
              Hold
            </button>
            <button onClick={() => void handleRestart()}>Restart</button>
          </div>

          <p style={{ fontSize: 12, opacity: 0.7, margin: "4px 0", maxWidth: 640 }}>
            Use Left / Right arrows to move, Down arrow to soft drop, Up arrow
            to rotate clockwise, the Z key to rotate counter-clockwise, and the
            C key (or Hold button) to hold a piece.
          </p>
        </>
      ) : (
        <p>Loading...</p>
      )}
    </section>
  );
}
