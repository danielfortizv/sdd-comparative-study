export interface ActivePiece {
  type: string;
  cells: [number, number][];
  origin: [number, number];
}

export interface GameState {
  id: string;
  board: (string | null)[][];
  active_piece: ActivePiece | null;
  status: string; // 'playing' | 'game_over'
  score: number;
  total_lines: number;
  level: number;
  gravity_interval_ms: number;
  next_piece: string;
  hold_piece: string | null;
  can_hold: boolean;
}

const API_BASE = "http://localhost:8000/api";

export async function createGame(): Promise<GameState> {
  const res = await fetch(`${API_BASE}/games`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to create game");
  return res.json();
}

export async function getGame(id: string): Promise<GameState> {
  const res = await fetch(`${API_BASE}/games/${id}`);
  if (!res.ok) throw new Error("Failed to fetch game state");
  return res.json();
}

export async function moveGame(id: string, direction: "left" | "right" | "down"): Promise<GameState> {
  const res = await fetch(`${API_BASE}/games/${id}/move`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ direction }),
  });
  if (!res.ok) throw new Error("Failed to execute move");
  return res.json();
}

export async function tickGame(id: string): Promise<GameState> {
  const res = await fetch(`${API_BASE}/games/${id}/tick`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to tick game");
  return res.json();
}

export async function holdGame(id: string): Promise<GameState> {
  const res = await fetch(`${API_BASE}/games/${id}/hold`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Failed to execute hold");
  return res.json();
}
