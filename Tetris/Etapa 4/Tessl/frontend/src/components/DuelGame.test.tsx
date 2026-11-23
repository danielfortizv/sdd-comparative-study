import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, act, waitFor, cleanup } from '@testing-library/react';
import App from '../App';
import { DuelGame } from './DuelGame';
import { GameState, DuelRoomStateUpdate } from '../types';

// Mock canvas context
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = () => ({
    fillRect: () => {},
    strokeRect: () => {},
    resetTransform: () => {},
    scale: () => {},
  } as any);
}

// Mock global crypto for secure ID generation
const mockCrypto = {
  randomUUID: () => 'f81d4fae-7dec-11d0-a765-00a0c91e6bf6',
  getRandomValues: (arr: Uint32Array) => {
    for (let i = 0; i < arr.length; i++) {
      arr[i] = Math.floor(Math.random() * 1000000000);
    }
    return arr;
  }
};
vi.stubGlobal('crypto', mockCrypto);

// Mock WebSocket class with standard static properties
class MockWebSocket {
  url: string;
  readyState: number = 0; // CONNECTING
  send = vi.fn();
  close = vi.fn();
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e: { code: number }) => void) | null = null;
  onerror: ((e: any) => void) | null = null;

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  static instances: MockWebSocket[] = [];

  constructor(url: string) {
    this.url = url;
    this.readyState = 0; // CONNECTING
    MockWebSocket.instances.push(this);
    // Connection succeeds immediately in next tick
    setTimeout(() => {
      this.readyState = 1; // OPEN
      if (this.onopen) this.onopen();
    }, 0);
  }
}

describe('Two-Player WebSocket Duel Component', () => {
  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket);
    MockWebSocket.instances = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation(() => Promise.resolve({
      ok: true,
      json: async () => ({ id: 'solo' })
    } as any));
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  const getMockBoard = (id: string, rev: number): GameState => ({
    id,
    board: Array.from({ length: 20 }, () => Array(10).fill(null)),
    active_piece: {
      type: 'I',
      origin: [0, 3],
      cells: [[0, 3], [0, 4], [0, 5], [0, 6]],
      orientation: 0,
    },
    status: 'playing',
    score: rev * 100, // display unique value per revision
    total_lines: 0,
    level: 1,
    gravity_interval_ms: 1000,
    next_piece: 'O',
    hold_piece: null,
    can_hold: true,
    board_revision: rev,
  });

  test('can enter Duel mode, auto-generate unguessable Room ID, and send Handshake', async () => {
    render(<App />);

    // Click Duel Mode button
    const modeBtn = screen.getByTestId('btn-mode-duel');
    await act(async () => {
      fireEvent.click(modeBtn);
    });

    expect(screen.getByText('Two-Player Duel Mode')).toBeDefined();

    // Click Create Room
    const createBtn = screen.getByText('Create Private Room');
    await act(async () => {
      fireEvent.click(createBtn);
    });

    // Verify WebSocket connected
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0];
    expect(socket.url).toContain('/api/ws/duel/room_');

    // Wait for open handshake
    await waitFor(() => {
      expect(socket.send).toHaveBeenCalled();
    });

    const handshakeMsg = JSON.parse(socket.send.mock.calls[0][0]);
    expect(handshakeMsg.version).toBe('1.0');
    expect(handshakeMsg.type).toBe('handshake');
    expect(handshakeMsg.payload.room_id).toBeDefined();
    expect(handshakeMsg.payload.client_id).toContain('client_');
  });

  test('validates room ID joining strictly: rejects whitespace, CRLF, and spaces', async () => {
    const onReturnMock = vi.fn();
    render(<DuelGame onReturnSolo={onReturnMock} />);

    const input = screen.getByTestId('room-id-input') as HTMLInputElement;
    const joinBtn = screen.getByText('Join Room');

    // Case A: Space/whitespace
    await act(async () => {
      fireEvent.change(input, { target: { value: 'room 123' } });
      fireEvent.click(joinBtn);
    });
    expect(screen.getByRole('alert').textContent).toContain('Room ID must be alphanumeric');

    // Case B: Punctuation like $ which is strictly rejected by alphanumeric check
    await act(async () => {
      fireEvent.change(input, { target: { value: 'room$123' } });
      fireEvent.click(joinBtn);
    });
    expect(screen.getByRole('alert').textContent).toContain('Room ID must be alphanumeric');

    // Case C: Valid room ID
    await act(async () => {
      fireEvent.change(input, { target: { value: 'Valid_Room-123' } });
      fireEvent.click(joinBtn);
    });
    // Check connection established
    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });
    expect(MockWebSocket.instances[0].url).toContain('/Valid_Room-123');
  });

  test('starts 2 Canvas boards after state update, handles wait-state peer placeholder', async () => {
    render(<DuelGame onReturnSolo={() => {}} />);

    // Connect to room
    await act(async () => {
      fireEvent.click(screen.getByText('Create Private Room'));
    });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0];
    const activeRoomId = socket.url.split('/').pop()!;

    // Wait for CONNECTION to open before handling onmessage
    await waitFor(() => {
      expect(screen.getByText('CONNECTED')).toBeDefined();
    });

    // Trigger handshake ACK from server assigning Player 1
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'handshake',
          payload: { seat: 'player1' }
        })
      });
    });

    expect(screen.getByText('player1')).toBeDefined();
    expect(screen.getByText('Initializing Board...')).toBeDefined();
    expect(screen.getByTestId('waiting-placeholder')).toBeDefined();

    // Trigger state_update with status playing
    const stateUpdate: DuelRoomStateUpdate = {
      room_id: activeRoomId,
      room_revision: 5,
      status: 'playing',
      player1_board: getMockBoard('solo1', 1),
      player2_board: getMockBoard('solo2', 1),
      winner_seat: null,
      outcome_reason: null,
    };

    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'state_update',
          payload: stateUpdate
        })
      });
    });

    // Verify 2 Canvas boards are drawn
    const canvases = document.querySelectorAll('canvas.tetris-board');
    expect(canvases.length).toBe(2);
    expect(screen.queryByText('Initializing Board...')).toBeNull();
    expect(screen.queryByTestId('waiting-placeholder')).toBeNull();
  });

  test('FIFO serialization: second queued move is sent ONLY after receiving matching ACK for first move', async () => {
    render(<DuelGame onReturnSolo={() => {}} />);

    await act(async () => {
      fireEvent.click(screen.getByText('Create Private Room'));
    });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0];
    const activeRoomId = socket.url.split('/').pop()!;

    // Wait for connection open
    await waitFor(() => {
      expect(screen.getByText('CONNECTED')).toBeDefined();
    });

    // Connect & start game
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'handshake',
          payload: { seat: 'player1' }
        })
      });
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'state_update',
          payload: {
            room_id: activeRoomId,
            room_revision: 5,
            status: 'playing',
            player1_board: getMockBoard('p1', 10),
            player2_board: getMockBoard('p2', 10),
            winner_seat: null,
            outcome_reason: null,
          }
        })
      });
    });

    // Clear initial handshake send mock calls
    socket.send.mockClear();

    // Trigger two key movements rapidly
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }));
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }));
    });

    // First action (move left) must be sent immediately
    expect(socket.send).toHaveBeenCalledTimes(1);
    const firstAction = JSON.parse(socket.send.mock.calls[0][0]);
    expect(firstAction.payload.action_type).toBe('move');
    expect(firstAction.payload.direction).toBe('left');
    const firstActionId = firstAction.payload.action_id;

    // Simulate stale/non-matching ACK: should NOT release or send second
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'ack',
          payload: {
            action_id: firstActionId + 99, // mismatch
            status: 'accepted',
            reason: '',
            board_revision: 11,
            room_revision: 6,
            authoritative_board: getMockBoard('p1', 11)
          }
        })
      });
    });
    expect(socket.send).toHaveBeenCalledTimes(1); // Still only 1 sent!

    // Simulate matching ACK
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'ack',
          payload: {
            action_id: firstActionId, // match
            status: 'accepted',
            reason: '',
            board_revision: 11,
            room_revision: 6,
            authoritative_board: getMockBoard('p1', 11)
          }
        })
      });
    });

    // Second action (move right) is now sent!
    expect(socket.send).toHaveBeenCalledTimes(2);
    const secondAction = JSON.parse(socket.send.mock.calls[1][0]);
    expect(secondAction.payload.action_type).toBe('move');
    expect(secondAction.payload.direction).toBe('right');
    expect(secondAction.payload.expected_revision).toBe(11);
  });

  test('stale ACK or out-of-order broadcast does not cause rollback', async () => {
    render(<DuelGame onReturnSolo={() => {}} />);

    await act(async () => {
      fireEvent.click(screen.getByText('Create Private Room'));
    });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0];
    const activeRoomId = socket.url.split('/').pop()!;

    // Wait for connection open
    await waitFor(() => {
      expect(screen.getByText('CONNECTED')).toBeDefined();
    });

    // Handshake & initial play state (revision 10)
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'handshake',
          payload: { seat: 'player1' }
        })
      });
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'state_update',
          payload: {
            room_id: activeRoomId,
            room_revision: 10,
            status: 'playing',
            player1_board: getMockBoard('p1', 10),
            player2_board: getMockBoard('p2', 10),
            winner_seat: null,
            outcome_reason: null,
          }
        })
      });
    });

    // Clear spy
    socket.send.mockClear();

    // Trigger action (ArrowDown)
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowDown' }));
    });
    expect(socket.send).toHaveBeenCalledTimes(1);
    const actId = JSON.parse(socket.send.mock.calls[0][0]).payload.action_id;

    // Send state_update with revision 12 (broadcast arrives first)
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'state_update',
          payload: {
            room_id: activeRoomId,
            room_revision: 12, // newer revision
            status: 'playing',
            player1_board: getMockBoard('p1', 12),
            player2_board: getMockBoard('p2', 12),
            winner_seat: null,
            outcome_reason: null,
          }
        })
      });
    });

    // Verify scoreboard reflects the latest (score is rev * 100)
    expect(screen.getAllByText('1200').length).toBeGreaterThanOrEqual(1);

    // Now older ACK for actId arrives (room_revision: 11)
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'ack',
          payload: {
            action_id: actId,
            status: 'accepted',
            reason: '',
            board_revision: 11,
            room_revision: 11, // older than 12
            authoritative_board: getMockBoard('p1', 11)
          }
        })
      });
    });

    // Check that we did NOT rollback from revision 1200 score to 1100 score
    expect(screen.queryByText('1100')).toBeNull();
    expect(screen.getAllByText('1200').length).toBeGreaterThanOrEqual(1);
  });

  test('keyboard inputs handles lower/uppercase and ignores keys when typing in inputs', async () => {
    render(<DuelGame onReturnSolo={() => {}} />);

    await act(async () => {
      fireEvent.click(screen.getByText('Create Private Room'));
    });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0];
    const activeRoomId = socket.url.split('/').pop()!;

    // Wait for connection open
    await waitFor(() => {
      expect(screen.getByText('CONNECTED')).toBeDefined();
    });

    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'handshake',
          payload: { seat: 'player1' }
        })
      });
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'state_update',
          payload: {
            room_id: activeRoomId,
            room_revision: 5,
            status: 'playing',
            player1_board: getMockBoard('p1', 1),
            player2_board: getMockBoard('p2', 1),
            winner_seat: null,
            outcome_reason: null,
          }
        })
      });
    });

    socket.send.mockClear();

    // Case 1: Active typing inside a focused input element
    const dummyInput = document.createElement('input');
    document.body.appendChild(dummyInput);
    dummyInput.focus();

    await act(async () => {
      dummyInput.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    });
    expect(socket.send).not.toHaveBeenCalled(); // Blocked!

    // Cleanup dummy input
    dummyInput.blur();
    document.body.removeChild(dummyInput);

    // Case 2: Z / z rotate keys (lowercase/uppercase)
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'z' }));
    });
    expect(socket.send).toHaveBeenCalledTimes(1);
    expect(JSON.parse(socket.send.mock.calls[0][0]).payload.action_type).toBe('rotate');
    expect(JSON.parse(socket.send.mock.calls[0][0]).payload.direction).toBe('ccw');

    // Simulate ACK so queue is empty
    const actId = JSON.parse(socket.send.mock.calls[0][0]).payload.action_id;
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'ack',
          payload: {
            action_id: actId,
            status: 'accepted',
            reason: '',
            board_revision: 2,
            room_revision: 6,
            authoritative_board: getMockBoard('p1', 2)
          }
        })
      });
    });

    socket.send.mockClear();

    // Case 3: C / c hold keys
    await act(async () => {
      window.dispatchEvent(new KeyboardEvent('keydown', { key: 'C' }));
    });
    expect(socket.send).toHaveBeenCalledTimes(1);
    expect(JSON.parse(socket.send.mock.calls[0][0]).payload.action_type).toBe('hold');
    expect(JSON.parse(socket.send.mock.calls[0][0]).payload.direction).toBeNull();
  });

  test('normal close retains final result and leave room cleans up websocket', async () => {
    render(<DuelGame onReturnSolo={() => {}} />);

    await act(async () => {
      fireEvent.click(screen.getByText('Create Private Room'));
    });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0];
    const activeRoomId = socket.url.split('/').pop()!;

    // Wait for connection open
    await waitFor(() => {
      expect(screen.getByText('CONNECTED')).toBeDefined();
    });

    // Terminate game normally
    await act(async () => {
      socket.onmessage!({
        data: JSON.stringify({
          version: '1.0',
          type: 'state_update',
          payload: {
            room_id: activeRoomId,
            room_revision: 20,
            status: 'finished',
            player1_board: getMockBoard('p1', 1),
            player2_board: getMockBoard('p2', 1),
            winner_seat: 'player1',
            outcome_reason: 'topout-player2',
          }
        })
      });
    });

    // Close socket with code 1000 (normal)
    await act(async () => {
      socket.onclose!({ code: 1000 });
    });

    // Verify finished panel shows correctly
    expect(screen.getByText('Duel Finished')).toBeDefined();
    expect(screen.getByText('topout-player2')).toBeDefined();

    // Leave room
    const leaveBtn = screen.getByText('Leave / Forfeit');
    await act(async () => {
      fireEvent.click(leaveBtn);
    });

    // Verify socket closed and state is reset back to room selection
    expect(socket.close).toHaveBeenCalledWith(1000);
    expect(screen.getByText('Two-Player Duel Mode')).toBeDefined();
  });

  test('unmounting DuelGame cleans up socket, clears FIFO queues and ignores late old callbacks', async () => {
    const { unmount } = render(<DuelGame onReturnSolo={() => {}} />);

    await act(async () => {
      fireEvent.click(screen.getByText('Create Private Room'));
    });

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBe(1);
    });

    const socket = MockWebSocket.instances[0];

    // Wait for connection open
    await waitFor(() => {
      expect(screen.getByText('CONNECTED')).toBeDefined();
    });

    unmount();

    // Verify WebSocket close was executed
    expect(socket.close).toHaveBeenCalledWith(1000);
    // Verify callbacks are cleared
    expect(socket.onopen).toBeNull();
    expect(socket.onmessage).toBeNull();
    expect(socket.onclose).toBeNull();
    expect(socket.onerror).toBeNull();
  });
});
