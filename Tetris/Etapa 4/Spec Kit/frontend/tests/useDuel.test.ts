import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDuel } from '../src/hooks/useDuel';

// Mock WebSocket class
class MockWebSocket {
  static instances: MockWebSocket[] = [];

  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  CONNECTING = 0;
  OPEN = 1;
  CLOSING = 2;
  CLOSED = 3;

  url: string;
  readyState: number;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  send: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;

  constructor(url: string) {
    this.url = url;
    this.readyState = MockWebSocket.CONNECTING;
    this.send = vi.fn();
    this.close = vi.fn().mockImplementation(() => {
      this.readyState = MockWebSocket.CLOSED;
      if (this.onclose) {
        this.onclose({ code: 1000 });
      }
    });
    MockWebSocket.instances.push(this);
  }

  triggerOpen() {
    this.readyState = MockWebSocket.OPEN;
    if (this.onopen) {
      this.onopen();
    }
  }

  triggerMessage(data: any) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }

  triggerError() {
    if (this.onerror) {
      this.onerror();
    }
  }

  triggerClose(code: number) {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code });
    }
  }
}

// Assign global mock
const originalWebSocket = globalThis.WebSocket;

describe('useDuel React Hook', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    globalThis.WebSocket = MockWebSocket as any;
    vi.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    globalThis.WebSocket = originalWebSocket;
    vi.restoreAllMocks();
  });

  it('should initialize with default states', () => {
    const { result } = renderHook(() => useDuel());

    expect(result.current.roomId).toBeNull();
    expect(result.current.assignedSeat).toBeNull();
    expect(result.current.roomState).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it('should automatically connect if initialRoomId is provided', () => {
    renderHook(() => useDuel('room-abc'));

    expect(MockWebSocket.instances).toHaveLength(1);
    expect(MockWebSocket.instances[0].url).toContain('room_id=room-abc');
  });

  it('should set loading when connecting and clear loading when opened', () => {
    const { result } = renderHook(() => useDuel());

    expect(result.current.loading).toBe(false);

    act(() => {
      result.current.connect('room-123');
    });

    expect(result.current.loading).toBe(true);
    expect(MockWebSocket.instances).toHaveLength(1);
    const mockWS = MockWebSocket.instances[0];

    act(() => {
      mockWS.triggerOpen();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should process joined event to set room ID and assigned seat', () => {
    const { result } = renderHook(() => useDuel());

    act(() => {
      result.current.connect('room-xyz');
    });

    const mockWS = MockWebSocket.instances[0];
    act(() => {
      mockWS.triggerOpen();
    });

    // Simulate server 'joined' event
    act(() => {
      mockWS.triggerMessage({
        v: 1,
        event: 'joined',
        payload: {
          room_id: 'room-xyz',
          assigned_seat: 'seat_1'
        }
      });
    });

    expect(result.current.roomId).toBe('room-xyz');
    expect(result.current.assignedSeat).toBe('seat_1');
  });

  it('should process state_update and reject stale revisions', () => {
    const { result } = renderHook(() => useDuel());

    act(() => {
      result.current.connect('room-xyz');
    });

    const mockWS = MockWebSocket.instances[0];
    act(() => {
      mockWS.triggerOpen();
      mockWS.triggerMessage({
        v: 1,
        event: 'joined',
        payload: { room_id: 'room-xyz', assigned_seat: 'seat_1' }
      });
    });

    const initialBoard = Array(20).fill(null).map(() => Array(10).fill(0));
    const samplePlayerState = {
      player_id: 'p1',
      board: initialBoard,
      active_piece: null,
      active_piece_generation: 0,
      last_processed_seq_num: 0,
      score: 100,
      total_lines: 0,
      level: 1,
      status: 'waiting',
      next_piece: 'I',
      hold_piece: null,
      can_hold: true
    };

    // Revision 5 state update
    act(() => {
      mockWS.triggerMessage({
        v: 1,
        event: 'state_update',
        payload: {
          room_id: 'room-xyz',
          status: 'active',
          last_action_seat: null,
          last_action_seq: null,
          last_action_observable_change: false,
          seat_1: samplePlayerState,
          seat_2: null,
          outcome: null,
          reason: null,
          revision: 5
        }
      });
    });

    expect(result.current.roomState).not.toBeNull();
    expect(result.current.roomState?.revision).toBe(5);
    expect(result.current.roomState?.seat_1?.score).toBe(100);

    // Stale revision 4 state update (should be ignored)
    act(() => {
      mockWS.triggerMessage({
        v: 1,
        event: 'state_update',
        payload: {
          room_id: 'room-xyz',
          status: 'active',
          last_action_seat: null,
          last_action_seq: null,
          last_action_observable_change: false,
          seat_1: { ...samplePlayerState, score: 999 },
          seat_2: null,
          outcome: null,
          reason: null,
          revision: 4
        }
      });
    });

    expect(result.current.roomState?.revision).toBe(5);
    expect(result.current.roomState?.seat_1?.score).toBe(100); // kept score 100

    // Newer revision 6 state update (should be accepted)
    act(() => {
      mockWS.triggerMessage({
        v: 1,
        event: 'state_update',
        payload: {
          room_id: 'room-xyz',
          status: 'active',
          last_action_seat: null,
          last_action_seq: null,
          last_action_observable_change: false,
          seat_1: { ...samplePlayerState, score: 200 },
          seat_2: null,
          outcome: null,
          reason: null,
          revision: 6
        }
      });
    });

    expect(result.current.roomState?.revision).toBe(6);
    expect(result.current.roomState?.seat_1?.score).toBe(200);
  });

  it('should handle game_over frame and transition status to finished', () => {
    const { result } = renderHook(() => useDuel());

    act(() => {
      result.current.connect('room-xyz');
    });

    const mockWS = MockWebSocket.instances[0];
    act(() => {
      mockWS.triggerOpen();
      mockWS.triggerMessage({
        v: 1,
        event: 'joined',
        payload: { room_id: 'room-xyz', assigned_seat: 'seat_1' }
      });
    });

    // Send an initial state so we have a roomState to modify
    act(() => {
      mockWS.triggerMessage({
        v: 1,
        event: 'state_update',
        payload: {
          room_id: 'room-xyz',
          status: 'active',
          last_action_seat: null,
          last_action_seq: null,
          last_action_observable_change: false,
          seat_1: null,
          seat_2: null,
          outcome: null,
          reason: null,
          revision: 1
        }
      });
    });

    // Send game_over message
    act(() => {
      mockWS.triggerMessage({
        v: 1,
        event: 'game_over',
        payload: {
          outcome: 'seat_2_win',
          reason: 'Seat 1 topped out'
        }
      });
    });

    expect(result.current.roomState?.status).toBe('finished');
    expect(result.current.roomState?.outcome).toBe('seat_2_win');
    expect(result.current.roomState?.reason).toBe('Seat 1 topped out');
  });

  it('should handle error WS message event', () => {
    const { result } = renderHook(() => useDuel());

    act(() => {
      result.current.connect('room-xyz');
    });

    const mockWS = MockWebSocket.instances[0];
    act(() => {
      mockWS.triggerOpen();
      mockWS.triggerMessage({
        v: 1,
        event: 'error',
        payload: {
          message: 'Invalid room ID format'
        }
      });
    });

    expect(result.current.error).toBe('Invalid room ID format');
  });

  it('should set error message on WebSocket connection error', () => {
    const { result } = renderHook(() => useDuel());

    act(() => {
      result.current.connect('room-xyz');
    });

    const mockWS = MockWebSocket.instances[0];
    act(() => {
      mockWS.triggerError();
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBe('Connection error or unauthorized origin');
  });

  it('should handle various WebSocket close codes', () => {
    const testCloseCode = (code: number, expectedError: string) => {
      const { result } = renderHook(() => useDuel());
      act(() => {
        result.current.connect('room-abc');
      });
      const mockWS = MockWebSocket.instances[MockWebSocket.instances.length - 1];
      act(() => {
        mockWS.triggerOpen();
        mockWS.triggerClose(code);
      });
      expect(result.current.error).toBe(expectedError);
    };

    testCloseCode(4001, 'Room is Full (Close Code 4001)');
    testCloseCode(4004, 'Room Invalid or Already Finished (Close Code 4004)');
    testCloseCode(4008, 'Connection Closed: Idle Timeout (Close Code 4008)');
    testCloseCode(1005, 'Disconnected: Close Code 1005');
  });

  it('should send action with monotonic sequence number and correct generation', () => {
    const { result } = renderHook(() => useDuel());

    act(() => {
      result.current.connect('room-xyz');
    });

    const mockWS = MockWebSocket.instances[0];
    act(() => {
      mockWS.triggerOpen();
      mockWS.triggerMessage({
        v: 1,
        event: 'joined',
        payload: { room_id: 'room-xyz', assigned_seat: 'seat_1' }
      });
    });

    // Provide initial state setting generation to 12
    act(() => {
      mockWS.triggerMessage({
        v: 1,
        event: 'state_update',
        payload: {
          room_id: 'room-xyz',
          status: 'active',
          last_action_seat: null,
          last_action_seq: null,
          last_action_observable_change: false,
          seat_1: {
            player_id: 'p1',
            board: Array(20).fill(null).map(() => Array(10).fill(0)),
            active_piece: null,
            active_piece_generation: 12,
            last_processed_seq_num: 0,
            score: 0,
            total_lines: 0,
            level: 1,
            status: 'playing',
            next_piece: 'I',
            hold_piece: null,
            can_hold: true
          },
          seat_2: null,
          outcome: null,
          reason: null,
          revision: 1
        }
      });
    });

    // Send actions
    act(() => {
      result.current.sendAction('left');
    });

    expect(mockWS.send).toHaveBeenCalledTimes(1);
    expect(JSON.parse(mockWS.send.mock.calls[0][0])).toEqual({
      v: 1,
      event: 'action',
      payload: {
        seq_num: 1,
        generation: 12,
        action_type: 'left'
      }
    });

    act(() => {
      result.current.sendAction('cw');
    });

    expect(mockWS.send).toHaveBeenCalledTimes(2);
    expect(JSON.parse(mockWS.send.mock.calls[1][0])).toEqual({
      v: 1,
      event: 'action',
      payload: {
        seq_num: 2,
        generation: 12,
        action_type: 'cw'
      }
    });
  });

  it('should ignore sendAction if WebSocket is not open or seat is not assigned', () => {
    const { result } = renderHook(() => useDuel());

    // Call connect but don't open WS yet
    act(() => {
      result.current.connect('room-xyz');
    });

    const mockWS = MockWebSocket.instances[0];

    act(() => {
      result.current.sendAction('left');
    });

    expect(mockWS.send).not.toHaveBeenCalled();
  });

  it('should discard messages and events from older closed sockets', () => {
    const { result } = renderHook(() => useDuel());

    // Connect 1st time
    act(() => {
      result.current.connect('room-1');
    });
    const mockWS1 = MockWebSocket.instances[0];

    // Connect 2nd time (replaces socket)
    act(() => {
      result.current.connect('room-2');
    });
    const mockWS2 = MockWebSocket.instances[1];

    act(() => {
      mockWS2.triggerOpen();
      mockWS2.triggerMessage({
        v: 1,
        event: 'joined',
        payload: { room_id: 'room-2', assigned_seat: 'seat_2' }
      });
    });

    expect(result.current.roomId).toBe('room-2');
    expect(result.current.assignedSeat).toBe('seat_2');

    // Message on older ws1 should be completely ignored
    act(() => {
      mockWS1.triggerMessage({
        v: 1,
        event: 'joined',
        payload: { room_id: 'room-1', assigned_seat: 'seat_1' }
      });
    });

    // State should still match socket 2
    expect(result.current.roomId).toBe('room-2');
    expect(result.current.assignedSeat).toBe('seat_2');
  });

  it('should clean up and close WS on unmount', () => {
    const { result, unmount } = renderHook(() => useDuel('room-123'));

    expect(MockWebSocket.instances).toHaveLength(1);
    const mockWS = MockWebSocket.instances[0];

    act(() => {
      mockWS.triggerOpen();
    });

    expect(result.current.loading).toBe(false);

    unmount();

    expect(mockWS.close).toHaveBeenCalled();
  });
});
