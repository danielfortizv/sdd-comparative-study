import { useState, useEffect, useRef, useCallback } from 'react';

export interface WSPlayerState {
  player_id: string;
  board: number[][];
  active_piece: {
    type: string;
    cells: [number, number][];
    origin: [number, number];
  } | null;
  active_piece_generation: number;
  last_processed_seq_num: number;
  score: number;
  total_lines: number;
  level: number;
  status: string;
  next_piece: string;
  hold_piece: string | null;
  can_hold: boolean;
}

export interface WSDuelRoomState {
  room_id: string;
  status: 'waiting' | 'active' | 'finished';
  last_action_seat: string | null;
  last_action_seq: number | null;
  last_action_observable_change: boolean;
  seat_1: WSPlayerState | null;
  seat_2: WSPlayerState | null;
  outcome: string | null;
  reason: string | null;
  revision: number;
}

export function useDuel(initialRoomId?: string) {
  const [roomId, setRoomId] = useState<string | null>(initialRoomId || null);
  const [assignedSeat, setAssignedSeat] = useState<'seat_1' | 'seat_2' | null>(null);
  const [roomState, setRoomState] = useState<WSDuelRoomState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const socketRef = useRef<WebSocket | null>(null);
  const seqNumRef = useRef<number>(1);
  const generationRef = useRef<number>(0);

  const currentSocketIdRef = useRef<string | null>(null);
  const lastRevisionRef = useRef<number>(-1);

  // Derive active piece generation of assigned seat
  useEffect(() => {
    if (roomState && assignedSeat) {
      const seatState = roomState[assignedSeat];
      if (seatState) {
        generationRef.current = seatState.active_piece_generation;
      }
    }
  }, [roomState, assignedSeat]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
    currentSocketIdRef.current = null;
    lastRevisionRef.current = -1;
    setRoomId(null);
    setRoomState(null);
    setAssignedSeat(null);
    seqNumRef.current = 1;
    generationRef.current = 0;
  }, []);

  const connect = useCallback((targetRoomId?: string) => {
    disconnect();
    setLoading(true);
    setError(null);

    const socketId = Date.now().toString() + Math.random().toString();
    currentSocketIdRef.current = socketId;
    lastRevisionRef.current = -1;

    const apiBase = (import.meta as any).env?.VITE_API_BASE || '';
    let wsUrl = '';
    
    if (apiBase.startsWith('http')) {
      wsUrl = apiBase.replace('http', 'ws') + '/duel/ws';
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      // Fallback for native execution port 5183/5173
      const host = window.location.host || 'localhost:5173';
      wsUrl = `${protocol}//${host}/api/duel/ws`;
    }

    if (targetRoomId) {
      wsUrl += `?room_id=${targetRoomId}`;
    }

    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      if (currentSocketIdRef.current !== socketId) {
        ws.close();
        return;
      }
      setLoading(false);
      logger('WebSocket connected to: ' + wsUrl);
    };

    ws.onmessage = (event) => {
      if (currentSocketIdRef.current !== socketId) {
        // Discard any messages from older closed sockets
        return;
      }
      try {
        const data = JSON.parse(event.data);
        if (data.v !== 1) return;

        switch (data.event) {
          case 'joined':
            setRoomId(data.payload.room_id);
            setAssignedSeat(data.payload.assigned_seat);
            break;

          case 'state_update': {
            const revision = data.payload.revision;
            if (typeof revision === 'number' && revision <= lastRevisionRef.current) {
              // Ignore stale or out-of-order revision updates
              logger(`Ignoring stale revision: received ${revision}, last was ${lastRevisionRef.current}`);
              return;
            }
            lastRevisionRef.current = revision;
            setRoomState(data.payload);
            break;
          }

          case 'game_over':
            setRoomState(prev => prev ? {
              ...prev,
              status: 'finished',
              outcome: data.payload.outcome,
              reason: data.payload.reason
            } : null);
            break;

          case 'error':
            setError(data.payload.message);
            break;

          default:
            break;
        }
      } catch (err) {
        logger('Error parsing WS frame: ' + err);
      }
    };

    ws.onerror = () => {
      if (currentSocketIdRef.current !== socketId) {
        return;
      }
      setLoading(false);
      setError('Connection error or unauthorized origin');
    };

    ws.onclose = (event) => {
      if (currentSocketIdRef.current !== socketId) {
        return;
      }
      setLoading(false);
      if (event.code === 4001) {
        setError('Room is Full (Close Code 4001)');
      } else if (event.code === 4004) {
        setError('Room Invalid or Already Finished (Close Code 4004)');
      } else if (event.code === 4008) {
        setError('Connection Closed: Idle Timeout (Close Code 4008)');
      } else if (event.code !== 1000) {
        setError(`Disconnected: Close Code ${event.code}`);
      }
      logger('WebSocket connection closed.');
    };
  }, [disconnect]);

  const sendAction = useCallback((actionType: 'left' | 'right' | 'down' | 'cw' | 'ccw' | 'hold') => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !assignedSeat) {
      return;
    }

    const currentSeq = seqNumRef.current++;
    const payload = {
      v: 1,
      event: 'action',
      payload: {
        seq_num: currentSeq,
        generation: generationRef.current,
        action_type: actionType
      }
    };

    ws.send(JSON.stringify(payload));
  }, [assignedSeat]);

  useEffect(() => {
    if (initialRoomId) {
      connect(initialRoomId);
    }
    return () => {
      disconnect();
    };
  }, [initialRoomId, connect, disconnect]);

  function logger(msg: string) {
    console.log('[useDuel]', msg);
  }

  return {
    roomId,
    assignedSeat,
    roomState,
    error,
    loading,
    connect,
    disconnect,
    sendAction
  };
}
