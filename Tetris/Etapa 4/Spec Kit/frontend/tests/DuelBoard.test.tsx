import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { DuelBoard } from '../src/components/DuelBoard';
import { WSDuelRoomState, WSPlayerState } from '../hooks/useDuel';

describe('DuelBoard Component', () => {
  const sendActionMock = vi.fn();
  const disconnectMock = vi.fn();

  // Mock Canvas 2D methods
  let fillRectSpy = vi.fn();
  let strokeRectSpy = vi.fn();
  let scaleSpy = vi.fn();
  let fillTextSpy = vi.fn();

  let resizeObserverCallback: (() => void) | null = null;

  beforeEach(() => {
    vi.clearAllMocks();

    fillRectSpy = vi.fn();
    strokeRectSpy = vi.fn();
    scaleSpy = vi.fn();
    fillTextSpy = vi.fn();

    // Mock Canvas Context
    HTMLCanvasElement.prototype.getContext = vi.fn().mockImplementation((contextId) => {
      if (contextId === '2d') {
        return {
          fillRect: fillRectSpy,
          strokeRect: strokeRectSpy,
          scale: scaleSpy,
          fillText: fillTextSpy,
          clearRect: vi.fn(),
          beginPath: vi.fn(),
          moveTo: vi.fn(),
          lineTo: vi.fn(),
          stroke: vi.fn(),
          fill: vi.fn(),
          fillStyle: '',
          strokeStyle: '',
          font: '',
          textAlign: '',
          lineWidth: 1,
        };
      }
      return null;
    });

    // Mock ResizeObserver
    globalThis.ResizeObserver = vi.fn().mockImplementation(function(callback) {
      resizeObserverCallback = callback;
      return {
        observe: vi.fn(),
        unobserve: vi.fn(),
        disconnect: vi.fn(),
      };
    });

    // Device Pixel Ratio default mock
    Object.defineProperty(window, 'devicePixelRatio', {
      writable: true,
      configurable: true,
      value: 2,
    });
  });

  afterEach(() => {
    resizeObserverCallback = null;
    vi.restoreAllMocks();
  });

  const createMockPlayerState = (overrides = {}): WSPlayerState => {
    const emptyBoard = Array(20).fill(null).map(() => Array(10).fill(0));
    return {
      player_id: 'player-1',
      board: emptyBoard,
      active_piece: {
        type: 'I',
        cells: [[0, 3], [0, 4], [0, 5], [0, 6]],
        origin: [0, 3],
      },
      active_piece_generation: 1,
      last_processed_seq_num: 10,
      score: 1200,
      total_lines: 8,
      level: 3,
      status: 'playing',
      next_piece: 'O',
      hold_piece: 'T',
      can_hold: true,
      ...overrides,
    };
  };

  const createMockRoomState = (overrides = {}): WSDuelRoomState => {
    return {
      room_id: 'room-123',
      status: 'active',
      last_action_seat: null,
      last_action_seq: null,
      last_action_observable_change: false,
      seat_1: createMockPlayerState(),
      seat_2: createMockPlayerState({ player_id: 'player-2', score: 800 }),
      outcome: null,
      reason: null,
      revision: 42,
      ...overrides,
    };
  };

  it('renders room header details correctly', () => {
    const roomState = createMockRoomState({ status: 'waiting', seat_2: null });
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    expect(screen.getByText('room-123')).not.toBeNull();
    expect(screen.getByText('WAITING')).not.toBeNull();
    expect(screen.getByText('Waiting for an opponent to join...')).not.toBeNull();
  });

  it('renders finished lobby panel when outcome is draw', () => {
    const roomState = createMockRoomState({ status: 'finished', outcome: 'draw', reason: 'Both topped out' });
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    expect(screen.getByText('DRAW!')).not.toBeNull();
    expect(screen.getByText('Both topped out')).not.toBeNull();
  });

  it('renders finished lobby victory/defeat messages', () => {
    // VICTORY for Seat 1
    const victoryState = createMockRoomState({ status: 'finished', outcome: 'seat_1_win', reason: 'Seat 2 topped out' });
    const { rerender } = render(
      <DuelBoard
        roomState={victoryState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );
    expect(screen.getByText('VICTORY!')).not.toBeNull();

    // DEFEAT for Seat 2
    rerender(
      <DuelBoard
        roomState={victoryState}
        assignedSeat="seat_2"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );
    expect(screen.getByText('DEFEAT!')).not.toBeNull();
  });

  it('renders stats DOM headers and panels for both players', () => {
    const roomState = createMockRoomState();
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    // Score displays
    expect(screen.getAllByText('1200')).toHaveLength(1); // seat_1 score
    expect(screen.getAllByText('800')).toHaveLength(1);  // seat_2 score
    
    // Seat identifiers
    expect(screen.getByText('Seat 1')).not.toBeNull();
    expect(screen.getByText('Seat 2')).not.toBeNull();
  });

  it('draws Waiting for player text if player state is vacant', () => {
    const roomState = createMockRoomState({ seat_2: null });
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    // Opponent seat is null, so it triggers "Waiting for player..." fillText on Canvas
    expect(fillTextSpy).toHaveBeenCalledWith('Waiting for player...', expect.any(Number), expect.any(Number));
  });

  it('draws board grid cells and active piece from player state', () => {
    // Fill board cell at [5, 5] with color index 3 (T-piece)
    const activeSeatState = createMockPlayerState();
    activeSeatState.board[5][5] = 3;

    const roomState = createMockRoomState({ seat_1: activeSeatState });
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    // fillRect must be called for drawing cells and background
    expect(fillRectSpy).toHaveBeenCalled();
    // It draws 200 vacant cells (case cellVal === 0: vacant transparent blocks, or full blocks)
    // Plus active piece blocks, plus background
    expect(fillRectSpy.mock.calls.length).toBeGreaterThan(200);
  });

  it('performs DPR pixel scaling and triggers draw on ResizeObserver callback', () => {
    const roomState = createMockRoomState();
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    // Default DPR is 2, so canvas is scaled by (2, 2)
    expect(scaleSpy).toHaveBeenCalledWith(2, 2);

    // Trigger simulated ResizeObserver change
    if (resizeObserverCallback) {
      fillRectSpy.mockClear();
      resizeObserverCallback();
      expect(fillRectSpy).toHaveBeenCalled();
    }
  });

  it('maps correct keyboard movement actions in active state', () => {
    const roomState = createMockRoomState({ status: 'active' });
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    const pressKey = (key: string) => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key }));
    };

    pressKey('ArrowLeft');
    expect(sendActionMock).toHaveBeenLastCalledWith('left');

    pressKey('ArrowRight');
    expect(sendActionMock).toHaveBeenLastCalledWith('right');

    pressKey('ArrowDown');
    expect(sendActionMock).toHaveBeenLastCalledWith('down');

    pressKey('ArrowUp');
    expect(sendActionMock).toHaveBeenLastCalledWith('cw');

    pressKey('z');
    expect(sendActionMock).toHaveBeenLastCalledWith('ccw');

    pressKey('Z');
    expect(sendActionMock).toHaveBeenLastCalledWith('ccw');

    pressKey('c');
    expect(sendActionMock).toHaveBeenLastCalledWith('hold');

    pressKey('C');
    expect(sendActionMock).toHaveBeenLastCalledWith('hold');

    pressKey('Shift');
    expect(sendActionMock).toHaveBeenLastCalledWith('hold');
  });

  it('suppresses keyboard actions when duel is not active', () => {
    const roomState = createMockRoomState({ status: 'waiting' });
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
    expect(sendActionMock).not.toHaveBeenCalled();
  });

  it('triggers exit action callback when button is clicked', () => {
    const roomState = createMockRoomState();
    render(
      <DuelBoard
        roomState={roomState}
        assignedSeat="seat_1"
        sendAction={sendActionMock}
        disconnect={disconnectMock}
      />
    );

    const exitBtn = screen.getByRole('button', { name: 'Exit Duel' });
    fireEvent.click(exitBtn);

    expect(disconnectMock).toHaveBeenCalledTimes(1);
  });
});
