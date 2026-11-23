// High Scores panel (Stage 3). Renders explicit loading / empty / error /
// loaded states. All visible text is in English. A failed fetch shows an error
// state without crashing the page (Req 8.1-8.4, 8.8).

import type { HighScoreEntry } from "./types";
import type { HighScoresStatus } from "./useHighScores";

interface HighScoresProps {
  readonly status: HighScoresStatus;
  readonly entries: readonly HighScoreEntry[];
}

export function HighScores({ status, entries }: HighScoresProps) {
  return (
    <section
      aria-label="High Scores"
      style={{ display: "flex", flexDirection: "column", gap: 8, minWidth: 180 }}
    >
      <h2 style={{ margin: 0, fontSize: 16 }}>High Scores</h2>

      {status === "loading" && (
        <p data-testid="highscores-loading">Loading high scores...</p>
      )}

      {status === "error" && (
        <p data-testid="highscores-error" style={{ color: "#f87171" }}>
          Could not load high scores.
        </p>
      )}

      {status === "empty" && (
        <p data-testid="highscores-empty">No high scores yet.</p>
      )}

      {status === "loaded" && (
        <ol data-testid="highscores-list" style={{ margin: 0, paddingLeft: 20 }}>
          {entries.map((entry) => (
            <li key={entry.game_id} data-testid="highscores-entry">
              <span data-testid="hs-score">Score: {entry.score}</span>
              {", "}
              <span data-testid="hs-lines">Lines: {entry.total_lines}</span>
              {", "}
              <span data-testid="hs-level">Level: {entry.level}</span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
