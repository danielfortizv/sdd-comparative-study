// Typed HTTP client for the backend game API.

import type { Direction, GameState } from "./types";

// Base URL for the backend; overridable via the VITE_API_BASE env var.
const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

async function asJson(response: Response): Promise<GameState> {
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as GameState;
}

// Create or restart a game.
export async function createGame(): Promise<GameState> {
  const response = await fetch(`${API_BASE}/api/games`, { method: "POST" });
  return asJson(response);
}

// Read the current state of a game.
export async function getGame(id: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/api/games/${id}`);
  return asJson(response);
}

// Advance one gravity tick.
export async function tickGame(id: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/api/games/${id}/tick`, {
    method: "POST",
  });
  return asJson(response);
}

// Move the active piece in the given direction.
export async function moveGame(
  id: string,
  direction: Direction,
): Promise<GameState> {
  const response = await fetch(`${API_BASE}/api/games/${id}/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction }),
  });
  return asJson(response);
}
