import { HighScoreEntry } from '../types';

interface HighScoresPanelProps {
  readonly scores?: HighScoreEntry[];
  readonly loading?: boolean;
  readonly error?: string | null;
}

export function HighScoresPanel({ scores = [], loading = false, error = null }: HighScoresPanelProps) {
  const safeScores = scores || [];
  return (
    <div className="high-scores-panel">
      <h3>High Scores Leaderboard</h3>
      {loading && <div className="scores-loading">Loading high scores...</div>}
      {error && <div className="scores-error">Error loading scores: {error}</div>}
      {!loading && !error && safeScores.length === 0 && (
        <div className="scores-empty">No high scores yet. Complete a game to set a score!</div>
      )}
      {!loading && !error && safeScores.length > 0 && (
        <table className="scores-table" style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #555', textAlign: 'left' }}>
              <th style={{ padding: '6px' }}>Rank</th>
              <th style={{ padding: '6px' }}>Score</th>
              <th style={{ padding: '6px' }}>Lines</th>
              <th style={{ padding: '6px' }}>Level</th>
            </tr>
          </thead>
          <tbody>
            {safeScores.slice(0, 10).map((entry, index) => (
              <tr key={entry.game_id} className="score-row" style={{ borderBottom: '1px solid #333' }}>
                <td className="score-rank" style={{ padding: '6px', fontWeight: 'bold', color: '#ffcc00' }}>
                  #{index + 1}
                </td>
                <td className="score-points" style={{ padding: '6px' }}>{entry.score}</td>
                <td className="score-lines" style={{ padding: '6px' }}>{entry.total_lines}</td>
                <td className="score-level" style={{ padding: '6px' }}>{entry.level}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
