import React from 'react';
import { GameState } from '../types';

interface GameStatusProps {
  gameState: GameState;
  onRestart: () => void;
  isLoading: boolean;
}

export const GameStatus: React.FC<GameStatusProps> = ({ gameState, onRestart, isLoading }) => {
  const { id, status, active_piece, score, total_lines, level, gravity_interval_ms } = gameState;

  return (
    <div className="game-status-panel">
      <h2>Game Status</h2>
      
      <div className="status-item">
        <span className="status-label">Session ID:</span>
        <span className="status-value session-id">{id}</span>
      </div>

      <div className="status-item">
        <span className="status-label">Status:</span>
        <span className={`status-value game-state-${status}`}>
          {status.toUpperCase()}
        </span>
      </div>

      <div className="status-item">
        <span className="status-label">Score:</span>
        <span className="status-value score-value">{score}</span>
      </div>

      <div className="status-item">
        <span className="status-label">Lines:</span>
        <span className="status-value lines-value">{total_lines}</span>
      </div>

      <div className="status-item">
        <span className="status-label">Level:</span>
        <span className="status-value level-value">{level}</span>
      </div>

      <div className="status-item">
        <span className="status-label">Gravity:</span>
        <span className="status-value gravity-value">{gravity_interval_ms} ms</span>
      </div>

      <div className="status-item">
        <span className="status-label">Active Piece:</span>
        <span className="status-value active-piece-type">
          {active_piece ? active_piece.type : 'None'}
        </span>
      </div>

      {status === 'game_over' && (
        <div className="game-over-banner">
          <h3>GAME OVER</h3>
          <p>Locked pieces reached the top!</p>
        </div>
      )}

      <div className="actions">
        <button 
          onClick={onRestart} 
          disabled={isLoading}
          className="btn-restart"
        >
          {isLoading ? 'Loading...' : 'Start New Game'}
        </button>
      </div>

      <div className="instructions">
        <h3>Controls</h3>
        <ul>
          <li><strong>Left:</strong> <kbd>ArrowLeft</kbd> (<kbd>←</kbd>)</li>
          <li><strong>Right:</strong> <kbd>ArrowRight</kbd> (<kbd>→</kbd>)</li>
          <li><strong>Down:</strong> <kbd>ArrowDown</kbd> (<kbd>↓</kbd>)</li>
          <li><strong>Hold:</strong> <kbd>C</kbd></li>
        </ul>
        <p className="note">Note: Piece rotation is not supported in Stage 2 Option A.</p>
      </div>
    </div>
  );
};
