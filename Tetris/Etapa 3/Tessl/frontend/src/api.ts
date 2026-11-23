import { GameState } from './types';

// Configurable API base URL, defaults to same-origin /api
const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '';
const GAMES_API_BASE = `${API_BASE_URL}/api/games`;
const HIGH_SCORES_API_BASE = `${API_BASE_URL}/api/high-scores`;

export interface HighScoreEntry {
  game_id: string;
  score: number;
  total_lines: number;
  level: number;
  completed_at: string;
}

export interface HighScoresResponse {
  scores: HighScoreEntry[];
}

export async function getHighScores(): Promise<HighScoresResponse> {
  const response = await fetch(HIGH_SCORES_API_BASE);
  if (!response.ok) {
    throw new Error('Failed to retrieve high scores');
  }
  return response.json();
}

export async function createGame(): Promise<GameState> {
  const response = await fetch(GAMES_API_BASE, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error('Failed to create game session');
  }
  return response.json();
}

export async function getGame(id: string): Promise<GameState> {
  const response = await fetch(`${GAMES_API_BASE}/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to retrieve game session ${id}`);
  }
  return response.json();
}

export async function tickGame(id: string): Promise<GameState> {
  const response = await fetch(`${GAMES_API_BASE}/${id}/tick`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to tick game session ${id}`);
  }
  return response.json();
}

export async function moveGame(id: string, direction: 'left' | 'right' | 'down'): Promise<GameState> {
  const response = await fetch(`${GAMES_API_BASE}/${id}/move`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ direction }),
  });
  if (!response.ok) {
    throw new Error(`Failed to move game session ${id} direction ${direction}`);
  }
  return response.json();
}

export async function holdGame(id: string): Promise<GameState> {
  const response = await fetch(`${GAMES_API_BASE}/${id}/hold`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to hold game session ${id}`);
  }
  return response.json();
}
