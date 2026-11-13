import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HighScoresPanel } from '../src/components/HighScoresPanel';
import { HighScoreEntry } from '../src/types';

describe('HighScoresPanel Component', () => {
  it('renders loading state correctly', () => {
    render(<HighScoresPanel scores={[]} loading={true} error={null} />);
    expect(screen.getByText('Loading high scores...')).not.toBeNull();
  });

  it('renders error state correctly', () => {
    render(<HighScoresPanel scores={[]} loading={false} error="Network Error" />);
    expect(screen.getByText('Error loading scores: Network Error')).not.toBeNull();
  });

  it('renders empty scores state correctly', () => {
    render(<HighScoresPanel scores={[]} loading={false} error={null} />);
    expect(screen.getByText('No high scores yet. Complete a game to set a score!')).not.toBeNull();
  });

  it('renders populated scores table correctly with correct fields', () => {
    const mockScores: HighScoreEntry[] = [
      {
        game_id: 'game-1',
        score: 1200,
        total_lines: 12,
        level: 2,
        completed_at: '2026-10-29T12:00:00Z',
      },
      {
        game_id: 'game-2',
        score: 500,
        total_lines: 5,
        level: 1,
        completed_at: '2026-10-29T13:00:00Z',
      },
    ];

    render(<HighScoresPanel scores={mockScores} loading={false} error={null} />);

    // Check title
    expect(screen.getByText('High Scores Leaderboard')).not.toBeNull();

    // Check columns
    expect(screen.getByText('Rank')).not.toBeNull();
    expect(screen.getByText('Score')).not.toBeNull();
    expect(screen.getByText('Lines')).not.toBeNull();
    expect(screen.getByText('Level')).not.toBeNull();

    // Check values
    expect(screen.getByText('#1')).not.toBeNull();
    expect(screen.getByText('1200')).not.toBeNull();
    expect(screen.getByText('12')).not.toBeNull();
    expect(screen.getByText('2')).not.toBeNull();

    expect(screen.getByText('#2')).not.toBeNull();
    expect(screen.getByText('500')).not.toBeNull();
    expect(screen.getByText('5')).not.toBeNull();
    expect(screen.getByText('1')).not.toBeNull();
  });
});
