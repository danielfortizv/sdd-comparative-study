import React from 'react';

interface GameOverModalProps {
  show: boolean;
  onRestart: () => void;
}

export const GameOverModal: React.FC<GameOverModalProps> = ({ show, onRestart }) => {
  if (!show) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <h2>Game Over</h2>
        <p>The blocks have reached the top!</p>
        <button className="restart-btn" onClick={onRestart}>
          Restart Game
        </button>
      </div>
    </div>
  );
};
