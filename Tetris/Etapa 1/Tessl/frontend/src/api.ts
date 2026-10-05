import { GameState } from './types';

const API_BASE = '/api/games';

export async function createGame(): Promise<GameState> {
  const response = await fetch(API_BASE, {
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
  const response = await fetch(`${API_BASE}/${id}`);
  if (!response.ok) {
    throw new Error(`Failed to retrieve game session ${id}`);
  }
  return response.json();
}

export async function tickGame(id: string): Promise<GameState> {
  const response = await fetch(`${API_BASE}/${id}/tick`, {
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
  const response = await fetch(`${API_BASE}/${id}/move`, {
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
