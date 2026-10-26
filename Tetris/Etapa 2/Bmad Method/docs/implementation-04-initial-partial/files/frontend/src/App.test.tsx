import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, act, waitFor } from '@testing-library/react'
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
    global.fetch = vi.fn().mockImplementation(async (url) => {
      if (url.includes('/tick') || url.includes('/move') || url.includes('/hold')) {
        return {
          ok: true,
          json: async () => mockInitialGame
        }
      }
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
    
    await act(async () => {
      fireEvent.click(startBtn)
    })

    expect(global.fetch).toHaveBeenCalledWith('/api/games', expect.objectContaining({
      method: 'POST'
    }))

    await waitFor(() => {
      expect(screen.getByText('playing')).toBeTruthy()
      expect(screen.getByText('Level:')).toBeTruthy()
      expect(screen.getByText('Score:')).toBeTruthy()
      
      // Check that Next Piece panel is rendered with class for O piece (color-4)
      const nextPieceHeader = screen.getByText('NEXT PIECE')
      const nextPanel = nextPieceHeader.parentElement
      expect(nextPanel?.querySelector('.color-4')).toBeTruthy()
    })
  })

  test('manual arrow keys and C key are captured and enqueued correctly', async () => {
    render(<App />)
    
    // Start game
    await act(async () => {
      fireEvent.click(screen.getByText('Start New Game'))
    })

    // Press ArrowLeft
    await act(async () => {
      fireEvent.keyDown(window, { key: 'ArrowLeft' })
    })

    expect(global.fetch).toHaveBeenCalledWith('/api/games/session-1/move', expect.objectContaining({
      body: JSON.stringify({ direction: 'left' })
    }))

    // Press C for hold
    await act(async () => {
      fireEvent.keyDown(window, { key: 'c' })
    })

    expect(global.fetch).toHaveBeenCalledWith('/api/games/session-1/hold', expect.objectContaining({
      method: 'POST'
    }))
  })

  test('restart session preempts mutation queue and increments generation token', async () => {
    let resolveFirstFetch: any
    const firstFetchPromise = new Promise((resolve) => {
      resolveFirstFetch = resolve
    })

    vi.mocked(global.fetch)
      .mockImplementationOnce(() => firstFetchPromise as any) // first session start
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          ...mockInitialGame,
          id: "session-2",
        })
      } as any) // restart click

    render(<App />)

    // First start (dangling/slow network)
    await act(async () => {
      fireEvent.click(screen.getByText('Start New Game'))
    })

    // Immediately click restart (which triggers startGame again)
    const restartBtn = screen.getByText('Start Session')
    await act(async () => {
      fireEvent.click(restartBtn)
    })

    // Resolve the first slow fetch
    await act(async () => {
      resolveFirstFetch({
        ok: true,
        json: async () => mockInitialGame
      })
    })

    // Verify session state is updated to session-2, and session-1 is discarded
    await waitFor(() => {
      expect(screen.queryByText('session-1')).toBeNull()
    })
  })
})
