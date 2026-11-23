import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GameOverModal } from '../src/components/GameOverModal';

describe('GameOverModal Component', () => {
  it('renders "Game Over" message and CTA button in English when show is true', () => {
    const handleRestart = vi.fn();
    render(<GameOverModal show={true} onRestart={handleRestart} />);
    
    expect(screen.getByText('Game Over')).not.toBeNull();
    expect(screen.getByText('The blocks have reached the top!')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Restart Game' })).not.toBeNull();
  });

  it('does not render anything when show is false', () => {
    const handleRestart = vi.fn();
    const { container } = render(<GameOverModal show={false} onRestart={handleRestart} />);
    expect(container.firstChild).toBeNull();
  });

  it('triggers onRestart callback when restart button is clicked', () => {
    const handleRestart = vi.fn();
    render(<GameOverModal show={true} onRestart={handleRestart} />);
    
    const button = screen.getByRole('button', { name: 'Restart Game' });
    fireEvent.click(button);
    
    expect(handleRestart).toHaveBeenCalledTimes(1);
  });
});
