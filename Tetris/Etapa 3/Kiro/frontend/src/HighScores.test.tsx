// Stage 3: High Scores panel states and fetch cadence (Req 8.1-8.8).

import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HighScores } from "./HighScores";
import type { HighScoreEntry } from "./types";

const sample: HighScoreEntry[] = [
  { game_id: "g1", score: 1200, total_lines: 13, level: 2, completed_at: "2026-01-01T00:00:00+00:00" },
  { game_id: "g2", score: 300, total_lines: 3, level: 1, completed_at: "2026-01-02T00:00:00+00:00" },
];

describe("HighScores panel states", () => {
  it("shows a loading state", () => {
    render(<HighScores status="loading" entries={[]} />);
    expect(screen.getByTestId("highscores-loading")).toHaveTextContent(/loading/i);
  });

  it("shows an empty state", () => {
    render(<HighScores status="empty" entries={[]} />);
    expect(screen.getByTestId("highscores-empty")).toHaveTextContent(/no high scores/i);
  });

  it("shows an error state without crashing", () => {
    render(<HighScores status="error" entries={[]} />);
    expect(screen.getByTestId("highscores-error")).toHaveTextContent(/could not load/i);
  });

  it("renders score, lines, and level for each loaded entry in English", () => {
    render(<HighScores status="loaded" entries={sample} />);
    const entries = screen.getAllByTestId("highscores-entry");
    expect(entries).toHaveLength(2);
    expect(entries[0]).toHaveTextContent("Score: 1200");
    expect(entries[0]).toHaveTextContent("Lines: 13");
    expect(entries[0]).toHaveTextContent("Level: 2");
  });
});
