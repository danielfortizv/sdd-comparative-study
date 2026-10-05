import React from 'react';

interface GameControlsProps {
  onRestart: () => void;
  status: string;
}

export const GameControls: React.FC<GameControlsProps> = ({ onRestart, status }) => {
  return (
    <div className="game-controls">
      <div className="controls-hint">
        <h3>Controls</h3>
        <p>Use <strong>Arrow Left</strong> / <strong>Right</strong> to move horizontally.</p>
        <p>Use <strong>Arrow Down</strong> to soft drop.</p>
      </div>
      <button className="restart-btn" onClick={onRestart}>
        {status === 'game_over' ? 'Play Again' : 'Restart Game'}
      </button>
    </div>
  );
};
