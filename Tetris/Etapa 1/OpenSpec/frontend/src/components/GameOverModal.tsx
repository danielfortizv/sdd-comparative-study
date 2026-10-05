interface GameOverModalProps {
  show: boolean;
  onRestart: () => void;
}

export default function GameOverModal({ show, onRestart }: GameOverModalProps) {
  if (!show) return null;

  return (
    <div className="modal-overlay" data-testid="game-over-modal">
      <div className="game-over-modal">
        <h2 className="glow-text">GAME OVER</h2>
        <p>The newly spawned piece collided with settled blocks.</p>
        <button className="neon-button modal-button" onClick={onRestart} data-testid="play-again-button">
          PLAY AGAIN
        </button>
      </div>
    </div>
  );
}
