// Typed HTTP client for the backend game API.

import type { Direction, GameState, HighScoresResponse } from "./types";

// Configurable API base. Default is the same-origin path prefix "/api" so the
// production build never hardcodes a localhost URL and works behind the Docker
// frontend proxy. Override with VITE_API_BASE for custom deployments.
const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function asJson(response: Response): Promise<GameState> {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as GameState;
}

// Create or restart a game.
export async function createGame(): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games`, { method: "POST" });
  return asJson(response);
}

// Read the current state of a game.
export async function getGame(id: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${id}`);
  return asJson(response);
}

// Advance one gravity tick.
export async function tickGame(id: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${id}/tick`, {
    method: "POST",
  });
  return asJson(response);
}

// Move the active piece in the given direction.
export async function moveGame(
  id: string,
  direction: Direction,
): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${id}/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction }),
  });
  return asJson(response);
}

// Rotate the active piece clockwise ("cw") or counter-clockwise ("ccw").
export async function rotateGame(
  id: string,
  direction: "cw" | "ccw",
): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${id}/rotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction }),
  });
  return asJson(response);
}

// Hold (or swap) the active piece.
export async function holdGame(id: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/games/${id}/hold`, {
    method: "POST",
  });
  return asJson(response);
}

// Read the top-ten leaderboard.
export async function getHighScores(): Promise<HighScoresResponse> {
  const response = await fetch(`${API_BASE}/high-scores`);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as HighScoresResponse;
}
