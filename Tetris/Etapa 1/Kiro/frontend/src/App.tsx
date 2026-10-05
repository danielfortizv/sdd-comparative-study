// Application shell: layout, keyboard controls, restart, and game-over message.

import { useEffect } from "react";

import { Board } from "./Board";
import { useGame } from "./useGame";

export function App() {
  const { state, error, move, restart } = useGame();

  // Map arrow keys to move commands while the game is playing.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!state || state.status !== "playing") {
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
      }
    }

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [state, move]);

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
      <h1>Tetris - Stage 1</h1>

      {error && <p style={{ color: "#f87171" }}>Error: {error}</p>}

      {state ? (
        <>
          <Board state={state} />

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
            <button onClick={() => void restart()}>Restart</button>
          </div>

          <p style={{ fontSize: 12, opacity: 0.7 }}>
            Use Left / Right arrows to move and Down arrow to soft drop.
          </p>
        </>
      ) : (
        <p>Loading...</p>
      )}
    </div>
  );
}
