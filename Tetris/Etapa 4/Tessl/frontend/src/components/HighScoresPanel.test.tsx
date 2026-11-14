import { describe, test, expect, vi, beforeAll, afterAll } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { HighScoresPanel } from './HighScoresPanel';

describe('HighScoresPanel Component', () => {
  beforeAll(() => {
    (globalThis as any).__TEST_HIGH_SCORES_EXPLICIT__ = true;
  });

  afterAll(() => {
    delete (globalThis as any).__TEST_HIGH_SCORES_EXPLICIT__;
  });

  test('renders loading state initially', async () => {
    vi.spyOn(globalThis, 'fetch');
    // Long-running promise to keep it in loading state
    (globalThis.fetch as any).mockReturnValueOnce(new Promise(() => {}));

    render(<HighScoresPanel trigger={0} />);

    expect(screen.getByTestId('high-scores-loading')).toBeDefined();
    expect(screen.getByText('Loading leaderboard...')).toBeDefined();
    
    vi.restoreAllMocks();
  });

  test('renders empty state when no high scores exist', async () => {
    vi.spyOn(globalThis, 'fetch');
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ scores: [] }),
    });

    render(<HighScoresPanel trigger={0} />);

    await waitFor(() => {
      expect(screen.queryByTestId('high-scores-loading')).toBeNull();
    });

    expect(screen.getByTestId('high-scores-empty')).toBeDefined();
    expect(screen.getByText(/No high scores yet/)).toBeDefined();

    vi.restoreAllMocks();
  });

  test('renders error state when fetch fails', async () => {
    vi.spyOn(globalThis, 'fetch');
    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: false,
    });

    render(<HighScoresPanel trigger={0} />);

    await waitFor(() => {
      expect(screen.queryByTestId('high-scores-loading')).toBeNull();
    });

    expect(screen.getByTestId('high-scores-error')).toBeDefined();
    expect(screen.getByText('Could not load high scores.')).toBeDefined();

    vi.restoreAllMocks();
  });

  test('renders high score entries correctly', async () => {
    vi.spyOn(globalThis, 'fetch');
    const mockScores = [
      { game_id: 'g1', score: 1250, total_lines: 10, level: 2, completed_at: '2026-11-02T10:00:00Z' },
      { game_id: 'g2', score: 500, total_lines: 4, level: 1, completed_at: '2026-11-02T09:00:00Z' }
    ];

    (globalThis.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ scores: mockScores }),
    });

    const { container } = render(<HighScoresPanel trigger={0} />);

    await waitFor(() => {
      expect(screen.queryByTestId('high-scores-loading')).toBeNull();
    });

    expect(screen.getByTestId('high-scores-list')).toBeDefined();
    expect(screen.getByText((1250).toLocaleString())).toBeDefined();
    expect(screen.getByText('500')).toBeDefined();
    
    // Check ranks
    const ranks = container.querySelectorAll('.score-rank');
    expect(ranks[0].textContent).toBe('1');
    expect(ranks[1].textContent).toBe('2');

    vi.restoreAllMocks();
  });
});
