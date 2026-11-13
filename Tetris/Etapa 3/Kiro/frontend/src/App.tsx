// Application shell: layout, keyboard controls, Hold, restart, the Stage 2
// sidebar (score / lines / level, next-piece preview, hold slot), and the
// Stage 3 High Scores panel.

import { useCallback, useEffect, useRef } from "react";

import { Board } from "./Board";
import { HighScores } from "./HighScores";
import { Preview } from "./Preview";
import { useGame } from "./useGame";
import { useHighScores } from "./useHighScores";

export function App() {
  const { state, error, move, hold, restart } = useGame();
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
      } else if (event.key === "c" || event.key === "C") {
        event.preventDefault();
        if (state.can_hold) {
          void hold();
        }
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [state, move, hold]);

  const holdDisabled =
    state?.status !== "playing" || !state.can_hold;

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 16,
        padding: 24,
        fontFamily: "system-ui, sans-serif",
        color: "#e5e7eb",
        background: "#0b1120",
      }}
    >
      <h1>Tetris - Stage 2</h1>

      {error && <p style={{ color: "#f87171" }}>Error: {error}</p>}

      {state ? (
        <>
          <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
            <Board state={state} />

            <aside
              aria-label="Game status"
              style={{ display: "flex", flexDirection: "column", gap: 12, minWidth: 140 }}
            >
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
            <p style={{ fontSize: 20, fontWeight: 700, color: "#f87171" }}>
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
            <button onClick={() => void hold()} disabled={holdDisabled}>
              Hold
            </button>
            <button onClick={() => void handleRestart()}>Restart</button>
          </div>

          <p style={{ fontSize: 12, opacity: 0.7 }}>
            Use Left / Right arrows to move, Down arrow to soft drop, and the C
            key (or Hold button) to hold a piece.
          </p>
        </>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}

