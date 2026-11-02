import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { createGame, getGame, tickGame, moveGame, holdGame } from './api';
import { GameState } from './types';

describe('api client functions', () => {
  const mockState: GameState = {
    id: 'test-api-uuid',
    board: [],
    active_piece: null,
    status: 'playing',
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: 'I',
    hold_piece: null,
    can_hold: true,
  };

  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch');
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('createGame calling POST /api/games', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockState,
    });

    const result = await createGame();
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/games', expect.objectContaining({ method: 'POST' }));
    expect(result).toEqual(mockState);
  });

  test('getGame calling GET /api/games/{id}', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockState,
    });

    const result = await getGame('test-api-uuid');
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/games/test-api-uuid');
    expect(result).toEqual(mockState);
  });

  test('tickGame calling POST /api/games/{id}/tick', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockState,
    });

    const result = await tickGame('test-api-uuid');
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/games/test-api-uuid/tick', expect.objectContaining({ method: 'POST' }));
    expect(result).toEqual(mockState);
  });

  test('moveGame calling POST /api/games/{id}/move', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockState,
    });

    const result = await moveGame('test-api-uuid', 'left');
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/games/test-api-uuid/move', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ direction: 'left' }),
    }));
    expect(result).toEqual(mockState);
  });

  test('holdGame calling POST /api/games/{id}/hold', async () => {
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => mockState,
    });

    const result = await holdGame('test-api-uuid');
    expect(globalThis.fetch).toHaveBeenCalledWith('/api/games/test-api-uuid/hold', expect.objectContaining({ method: 'POST' }));
    expect(result).toEqual(mockState);
  });

  test('handles fetch errors for all endpoints', async () => {
    (globalThis.fetch as any).mockResolvedValue({
      ok: false,
    });

    await expect(createGame()).rejects.toThrow('Failed to create game session');
    await expect(getGame('test-api-uuid')).rejects.toThrow('Failed to retrieve game session test-api-uuid');
    await expect(tickGame('test-api-uuid')).rejects.toThrow('Failed to tick game session test-api-uuid');
    await expect(moveGame('test-api-uuid', 'left')).rejects.toThrow('Failed to move game session test-api-uuid direction left');
    await expect(holdGame('test-api-uuid')).rejects.toThrow('Failed to hold game session test-api-uuid');
  });
});
