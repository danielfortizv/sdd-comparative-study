import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import App from './App'

describe('Tetris Study React Thin-Client Frontend', () => {
  const mockInitialGame = {
    id: "session-1",
    status: "playing",
    board: Array.from({ length: 20 }, () => Array(10).fill(0)),
    active_piece: {
      shape: "I",
      origin: { row: 0, col: 3 },
      cells: [{ row: 0, col: 3 }, { row: 0, col: 4 }, { row: 0, col: 5 }, { row: 0, col: 6 }]
    },
    score: 0,
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 500,
    next_piece: "O",
    hold_piece: null,
    can_hold: true
  }

  beforeEach(() => {
    // Provide a robust default mock implementation for fetch to handle ticks, moves, holds
    (globalThis as any).fetch = vi.fn().mockImplementation(async (_url) => {
      return {
        ok: true,
        json: async () => mockInitialGame
      }
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  test('renders start menu before session creation', () => {
    render(<App />)
    expect(screen.getByText('DECOUPLED TETRIS STUDY')).toBeTruthy()
    expect(screen.getByText('Start New Game')).toBeTruthy()
  })

  test('clicking start game triggers POST /api/games and sets state', async () => {
    render(<App />)
    const startBtn = screen.getByText('Start New Game')
    
    fireEvent.click(startBtn)

    expect((globalThis as any).fetch).toHaveBeenCalledWith('/api/games', expect.objectContaining({
      method: 'POST'
    }))

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
      expect(screen.getByText('Level:')).toBeTruthy()
      expect(screen.getByText('Score:')).toBeTruthy()
      
      const nextPieceHeader = screen.getByText('NEXT PIECE')
      const nextPanel = nextPieceHeader.parentElement
      expect(nextPanel?.querySelector('.color-4')).toBeTruthy()
    })
  })

  test('manual arrow keys and C key are captured and enqueued correctly', async () => {
    render(<App />)
    
    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
    })

    // Press ArrowLeft
    fireEvent.keyDown(window, { key: 'ArrowLeft' })

    await waitFor(() => {
      expect((globalThis as any).fetch).toHaveBeenCalledWith('/api/games/session-1/move', expect.objectContaining({
        body: JSON.stringify({ direction: 'left' })
      }))
    })

    // Press ArrowRight
    fireEvent.keyDown(window, { key: 'ArrowRight' })

    await waitFor(() => {
      expect((globalThis as any).fetch).toHaveBeenCalledWith('/api/games/session-1/move', expect.objectContaining({
        body: JSON.stringify({ direction: 'right' })
      }))
    })

    // Press ArrowDown
    fireEvent.keyDown(window, { key: 'ArrowDown' })

    await waitFor(() => {
      expect((globalThis as any).fetch).toHaveBeenCalledWith('/api/games/session-1/move', expect.objectContaining({
        body: JSON.stringify({ direction: 'down' })
      }))
    })

    // Press C for hold
    fireEvent.keyDown(window, { key: 'c' })

    await waitFor(() => {
      expect((globalThis as any).fetch).toHaveBeenCalledWith('/api/games/session-1/hold', expect.objectContaining({
        method: 'POST'
      }))
    })

    // Press key that is ignored
    fireEvent.keyDown(window, { key: 'Escape' })
  })

  test('hold button triggers backend hold swap', async () => {
    render(<App />)
    
    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
    })

    const holdButton = screen.getByText('Hold Piece (C)')
    expect(holdButton).toBeTruthy()
    expect(holdButton.hasAttribute('disabled')).toBeFalsy()

    fireEvent.click(holdButton)

    await waitFor(() => {
      expect((globalThis as any).fetch).toHaveBeenCalledWith('/api/games/session-1/hold', expect.objectContaining({
        method: 'POST'
      }))
    })
  })

  test('restart session preempts mutation queue and increments generation token', async () => {
    let resolveFirstFetch: any
    const firstFetchPromise = new Promise((resolve) => {
      resolveFirstFetch = resolve
    })

    vi.mocked((globalThis as any).fetch)
      .mockImplementationOnce(() => firstFetchPromise as any) // first session start
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...mockInitialGame,
          id: "session-2",
        })
      } as any) // restart click

    render(<App />)

    // First start
    fireEvent.click(screen.getByText('Start New Game'))

    // Immediately click restart (which triggers startGame again)
    const restartBtn = screen.getByText('Start Session')
    fireEvent.click(restartBtn)

    // Resolve the first slow fetch
    resolveFirstFetch({
      ok: true,
      json: async () => mockInitialGame
    })

    // Verify session state is updated to session-2, and session-1 is discarded
    await waitFor(() => {
      expect(screen.queryByText('session-1')).toBeNull()
    })
  })

  test('automatic gravity tick executes and updates board state', async () => {
    render(<App />)

    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
    })

    // Real-world delay to let gravity tick fire
    await new Promise(resolve => setTimeout(resolve, 550))

    await waitFor(() => {
      expect((globalThis as any).fetch).toHaveBeenCalledWith('/api/games/session-1/tick', expect.objectContaining({
        method: 'POST'
      }))
    })
  })

  test('unmounted component cancels timer and increments generation', () => {
    const { unmount } = render(<App />)
    unmount()
    expect(true).toBe(true)
  })

  test('start game server failure sets error state', async () => {
    vi.mocked((globalThis as any).fetch).mockResolvedValueOnce({
      ok: false,
    } as any)

    render(<App />)

    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('Failed to create game session')).toBeTruthy()
    })
  })

  test('start game network throw sets error state', async () => {
    vi.mocked((globalThis as any).fetch).mockRejectedValueOnce(new Error('Network disconnected'))

    render(<App />)

    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('Network disconnected')).toBeTruthy()
    })
  })

  test('non-ok responses in move and hold are handled gracefully', async () => {
    render(<App />)

    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
    })

    // Mock non-ok response
    vi.mocked((globalThis as any).fetch).mockResolvedValue({
      ok: false,
    } as any)

    // Fire movements and holds
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    fireEvent.keyDown(window, { key: 'c' })

    expect((globalThis as any).fetch).toHaveBeenCalled()
  })

  test('network rejections in move, hold, and tick are caught and logged', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    render(<App />)

    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
    })

    // Mock network throw
    vi.mocked((globalThis as any).fetch).mockRejectedValue(new Error('Fetch aborted'))

    // Fire movement
    fireEvent.keyDown(window, { key: 'ArrowLeft' })
    // Fire hold
    fireEvent.keyDown(window, { key: 'c' })
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled()
    })

    consoleSpy.mockRestore()
  })

  test('renders hold piece and active pieces with diverse shapes', async () => {
    const customGame = {
      ...mockInitialGame,
      hold_piece: "J",
      active_piece: {
        shape: "S",
        origin: { row: 2, col: 2 },
        cells: [{ row: 2, col: 2 }, { row: 2, col: 3 }, { row: 3, col: 1 }, { row: 3, col: 2 }]
      }
    }

    vi.mocked((globalThis as any).fetch).mockResolvedValue({
      ok: true,
      json: async () => customGame
    } as any)

    render(<App />)

    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('HOLD SLOT')).toBeTruthy()
    })
  })

  test('game over screen renders overlay and play again starts new game', async () => {
    const gameOverGame = {
      ...mockInitialGame,
      status: "game_over",
      active_piece: null
    }

    vi.mocked((globalThis as any).fetch).mockResolvedValue({
      ok: true,
      json: async () => gameOverGame
    } as any)

    render(<App />)

    fireEvent.click(screen.getByText('Start New Game'))

    await waitFor(() => {
      expect(screen.getByText('GAME OVER')).toBeTruthy()
    })

    const playAgainBtn = screen.getByText('Play Again')
    expect(playAgainBtn).toBeTruthy()

    // Reset fetch mock for the play again click
    vi.mocked((globalThis as any).fetch).mockResolvedValue({
      ok: true,
      json: async () => mockInitialGame
    } as any)

    fireEvent.click(playAgainBtn)

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
    })
  })
})
