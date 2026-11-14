import React, { useState, useEffect, useRef } from 'react';
import {
  GameState,
  DuelRoomStateUpdate,
  DuelServerMessage,
  ServerAckMessage,
  ServerStateUpdateMessage,
  ServerHandshakeMessage,
  SeatType
} from '../types';
import { TetrisBoard } from './TetrisBoard';
import { PiecePreview } from './PiecePreview';

interface DuelGameProps {
  onReturnSolo: () => void;
}

const generateSecureId = (prefix: string): string => {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return `${prefix}_${crypto.randomUUID()}`;
  }
  const array = new Uint32Array(4);
  crypto.getRandomValues(array);
  const hex = Array.from(array, dec => dec.toString(36)).join('');
  return `${prefix}_${hex}`;
};

export const DuelGame: React.FC<DuelGameProps> = ({ onReturnSolo }) => {
  const [inputRoomId, setInputRoomId] = useState('');
  const [roomId, setRoomId] = useState<string | null>(null);
  const [seat, setSeat] = useState<SeatType | null>(null);
  const [roomState, setRoomState] = useState<DuelRoomStateUpdate | null>(null);
  const [connStatus, setConnStatus] = useState<'idle' | 'connecting' | 'connected' | 'closed' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Refs to prevent React stale closure bugs in WebSocket callbacks
  const roomIdRef = useRef<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const seatRef = useRef<SeatType | null>(null);
  const roomStateRef = useRef<DuelRoomStateUpdate | null>(null);
  const actionIdRef = useRef<number>(1);
  const wsGenRef = useRef<number>(0);

  // FIFO Queue
  const queueRef = useRef<{ action_type: 'move' | 'hold' | 'rotate'; direction: 'left' | 'right' | 'down' | 'cw' | 'ccw' | null }[]>([]);
  const pendingActionRef = useRef<{ action_id: number; timeoutId: ReturnType<typeof setTimeout> } | null>(null);

  // Generate a unique, unguessable client ID per connection
  const [clientId] = useState(() => generateSecureId('client'));

  const validateRoomId = (id: string): boolean => {
    if (!id || id.length > 64) return false;
    // Reject LF/CR/CRLF/U2028/U2029 and whitespace
    if (/[\s\r\n\u2028\u2029]/.test(id)) return false;
    // Strictly alphanumeric, dashes, and underscores
    return /^[a-zA-Z0-9_-]+$/.test(id);
  };

  const handleCreateRoom = () => {
    const generatedId = generateSecureId('room');
    setErrorMessage(null);
    connectWebSocket(generatedId);
  };

  const handleJoinRoom = () => {
    const rawInput = inputRoomId;
    if (!rawInput) {
      setErrorMessage('Room ID cannot be empty.');
      return;
    }
    if (!validateRoomId(rawInput)) {
      setErrorMessage('Room ID must be alphanumeric, dashes, or underscores only (1-64 chars, no whitespace/newlines).');
      return;
    }
    setErrorMessage(null);
    connectWebSocket(rawInput);
  };

  const connectWebSocket = (targetRoomId: string) => {
    cleanupWebSocket();

    setRoomId(targetRoomId);
    roomIdRef.current = targetRoomId;
    setConnStatus('connecting');
    setErrorMessage(null);
    setSeat(null);
    seatRef.current = null;
    setRoomState(null);
    roomStateRef.current = null;
    actionIdRef.current = 1;
    queueRef.current = [];
    pendingActionRef.current = null;

    wsGenRef.current += 1;
    const currentWsGen = wsGenRef.current;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/ws/duel/${targetRoomId}`;

    let socket: WebSocket;
    try {
      socket = new WebSocket(wsUrl);
      socketRef.current = socket;
    } catch (e) {
      console.error(e);
      setConnStatus('error');
      setErrorMessage('Failed to create WebSocket instance.');
      return;
    }

    socket.onopen = () => {
      if (wsGenRef.current !== currentWsGen) return;
      setConnStatus('connected');
      // Send Handshake Immediately
      const handshake = {
        version: '1.0',
        type: 'handshake',
        payload: {
          room_id: targetRoomId,
          client_id: clientId,
        },
      };
      try {
        socket.send(JSON.stringify(handshake));
      } catch (err) {
        console.error('Failed to send handshake:', err);
      }
    };

    socket.onmessage = (event) => {
      if (wsGenRef.current !== currentWsGen) return;
      try {
        const data = JSON.parse(event.data) as DuelServerMessage;
        handleServerMessage(data);
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    socket.onclose = (event) => {
      if (wsGenRef.current !== currentWsGen) return;
      cleanupPendingAction();
      if (event.code === 1000) {
        setConnStatus('closed');
      } else {
        setConnStatus('error');
        setErrorMessage(`Disconnected from room (Code: ${event.code}).`);
      }
    };

    socket.onerror = (event) => {
      if (wsGenRef.current !== currentWsGen) return;
      console.error('WebSocket error:', event);
      setConnStatus('error');
      setErrorMessage('WebSocket connection encountered an error.');
      cleanupPendingAction();
    };
  };

  const cleanupPendingAction = () => {
    if (pendingActionRef.current) {
      clearTimeout(pendingActionRef.current.timeoutId);
      pendingActionRef.current = null;
    }
  };

  const cleanupWebSocket = () => {
    cleanupPendingAction();
    queueRef.current = [];
    wsGenRef.current += 1; // Invalidate current socket generation callback

    if (socketRef.current) {
      socketRef.current.onopen = null;
      socketRef.current.onmessage = null;
      socketRef.current.onclose = null;
      socketRef.current.onerror = null;
      if (socketRef.current.readyState === WebSocket.CONNECTING || socketRef.current.readyState === WebSocket.OPEN) {
        try {
          socketRef.current.close(1000);
        } catch (e) {
          console.error('Failed to close websocket safely:', e);
        }
      }
      socketRef.current = null;
    }
  };

  const handleServerMessage = (msg: DuelServerMessage) => {
    if (!msg || typeof msg !== 'object' || msg.version !== '1.0') return;

    if (msg.type === 'handshake') {
      const handshake = msg as ServerHandshakeMessage;
      setSeat(handshake.payload.seat);
      seatRef.current = handshake.payload.seat;
    } else if (msg.type === 'state_update') {
      const update = msg as ServerStateUpdateMessage;
      const newPayload = update.payload;
      if (newPayload.room_id !== roomIdRef.current) return;

      const currentRoom = roomStateRef.current;
      if (!currentRoom || newPayload.room_revision >= currentRoom.room_revision) {
        roomStateRef.current = newPayload;
        setRoomState(newPayload);
      }
    } else if (msg.type === 'ack') {
      const ack = msg as ServerAckMessage;
      if (pendingActionRef.current && pendingActionRef.current.action_id === ack.payload.action_id) {
        clearTimeout(pendingActionRef.current.timeoutId);
        pendingActionRef.current = null;

        const currentRoom = roomStateRef.current;
        const isAckNewerOrEqual = !currentRoom || ack.payload.room_revision >= currentRoom.room_revision;
        if (isAckNewerOrEqual) {
          const updated = currentRoom ? { ...currentRoom } : {
            room_id: roomIdRef.current || '',
            room_revision: ack.payload.room_revision,
            status: 'playing' as const,
            player1_board: null,
            player2_board: null,
            winner_seat: null,
            outcome_reason: null
          };

          if (seatRef.current === 'player1') {
            updated.player1_board = ack.payload.authoritative_board;
          } else if (seatRef.current === 'player2') {
            updated.player2_board = ack.payload.authoritative_board;
          }
          updated.room_revision = ack.payload.room_revision;

          roomStateRef.current = updated;
          setRoomState(updated);
        }

        // Send next queued action
        sendNextAction();
      }
    } else if (msg.type === 'error') {
      const code = msg.payload?.error_code ?? 'unknown';
      setErrorMessage(`Server error: ${msg.payload.message} (Code: ${code})`);
    }
  };

  const sendNextAction = () => {
    if (pendingActionRef.current) return;
    if (queueRef.current.length === 0) return;
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    if (!roomStateRef.current || roomStateRef.current.status !== 'playing') return;

    const nextCmd = queueRef.current.shift()!;
    const ownBoard = seatRef.current === 'player1' ? roomStateRef.current.player1_board : roomStateRef.current.player2_board;
    if (!ownBoard) return;

    let actionId = actionIdRef.current++;
    if (actionIdRef.current >= Number.MAX_SAFE_INTEGER - 100) {
      setErrorMessage("Action sequence limit reached (Integer Overflow Protection). Closing connection.");
      cleanupWebSocket();
      return;
    }

    const payload = {
      version: '1.0',
      type: 'action',
      payload: {
        action_id: actionId,
        expected_revision: ownBoard.board_revision,
        action_type: nextCmd.action_type,
        direction: nextCmd.direction,
      },
    };

    const timeoutId = setTimeout(() => {
      console.warn(`Action ID ${actionId} timeout`);
      setConnStatus('error');
      setErrorMessage('Action timeout: server failed to respond in 5 seconds.');
      cleanupWebSocket();
    }, 5000);

    pendingActionRef.current = {
      action_id: actionId,
      timeoutId,
    };

    try {
      socketRef.current.send(JSON.stringify(payload));
    } catch (err) {
      console.error('Failed to send WebSocket message:', err);
      setConnStatus('error');
      setErrorMessage('Failed to send player action.');
      cleanupWebSocket();
    }
  };

  const triggerAction = (actionType: 'move' | 'hold' | 'rotate', direction: 'left' | 'right' | 'down' | 'cw' | 'ccw' | null) => {
    if (!seatRef.current || roomStateRef.current?.status !== 'playing') return;
    const cleanDirection = actionType === 'hold' ? null : direction;
    queueRef.current.push({ action_type: actionType, direction: cleanDirection });
    sendNextAction();
  };

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) {
        return;
      }

      if (roomStateRef.current?.status !== 'playing' || !seatRef.current) return;

      let actionType: 'move' | 'hold' | 'rotate' | null = null;
      let direction: 'left' | 'right' | 'down' | 'cw' | 'ccw' | null = null;

      if (event.key === 'ArrowLeft') {
        actionType = 'move';
        direction = 'left';
      } else if (event.key === 'ArrowRight') {
        actionType = 'move';
        direction = 'right';
      } else if (event.key === 'ArrowDown') {
        actionType = 'move';
        direction = 'down';
      } else if (event.key === 'ArrowUp') {
        actionType = 'rotate';
        direction = 'cw';
      } else if (event.key === 'z' || event.key === 'Z') {
        actionType = 'rotate';
        direction = 'ccw';
      } else if (event.key === 'c' || event.key === 'C') {
        actionType = 'hold';
        direction = null;
      }

      if (actionType) {
        event.preventDefault();
        triggerAction(actionType, direction);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // Cleanup websocket on unmount
  useEffect(() => {
    return () => {
      cleanupWebSocket();
    };
  }, []);

  const handleLeaveRoom = () => {
    cleanupWebSocket();
    setRoomId(null);
    roomIdRef.current = null;
    setSeat(null);
    seatRef.current = null;
    setRoomState(null);
    roomStateRef.current = null;
    setConnStatus('idle');
    setErrorMessage(null);
  };

  const renderBoardStats = (board: GameState | null, playerLabel: string) => {
    if (!board) return null;
    return (
      <div className="duel-stats">
        <h4>{playerLabel}</h4>
        <div className="stats-row">
          <span>Score: <strong>{board.score}</strong></span>
          <span>Lines: <strong>{board.total_lines}</strong></span>
          <span>Lvl: <strong>{board.level}</strong></span>
        </div>
        <div className="duel-mini-grids">
          <div className="mini-grid-container">
            <span className="mini-label">Hold</span>
            <PiecePreview pieceType={board.hold_piece} />
          </div>
          <div className="mini-grid-container">
            <span className="mini-label">Next</span>
            <PiecePreview pieceType={board.next_piece} />
          </div>
        </div>
      </div>
    );
  };

  // 1. Pre-connection state (Room Selection Form)
  if (roomId === null) {
    return (
      <div className="panel duel-setup-panel">
        <h3>Two-Player Duel Mode</h3>
        <p className="description">
          Create a new private room or join an existing room to play a real-time Tetris duel.
        </p>

        {errorMessage && <p className="error-message" role="alert">{errorMessage}</p>}

        <div className="setup-actions">
          <button onClick={handleCreateRoom} className="btn-primary btn-create">
            Create Private Room
          </button>

          <div className="divider"><span>OR</span></div>

          <div className="join-form">
            <label htmlFor="room-id-input" className="sr-only">Join Room ID</label>
            <input
              id="room-id-input"
              type="text"
              placeholder="Enter Room ID"
              value={inputRoomId}
              onChange={(e) => setInputRoomId(e.target.value)}
              className="room-input"
              data-testid="room-id-input"
              aria-label="Join Room ID"
            />
            <button onClick={handleJoinRoom} className="btn-secondary btn-join">
              Join Room
            </button>
          </div>
        </div>

        <button onClick={onReturnSolo} className="btn-return">
          Return to Solo Mode
        </button>
      </div>
    );
  }

  // 2. Connected state (Dual Board view)
  const isPlaying = roomState?.status === 'playing';
  const isFinished = roomState?.status === 'finished';

  return (
    <div className="duel-container">
      <div className="duel-header">
        <div className="room-info">
          <span>Room: <strong className="room-id-display">{roomId}</strong></span>
          <span>Seat: <strong className="seat-display">{seat || 'Assigning...'}</strong></span>
          <span>Status: <strong className="conn-status-display">{connStatus.toUpperCase()}</strong></span>
        </div>
        <button onClick={handleLeaveRoom} className="btn-leave">
          Leave / Forfeit
        </button>
      </div>

      {errorMessage && <div className="error-panel"><p className="error-message" role="alert">{errorMessage}</p></div>}

      {isFinished && roomState && (
        <div className="panel outcome-panel">
          <h3>Duel Finished</h3>
          <p className="outcome-winner">
            Winner: <strong>{roomState.winner_seat ? (roomState.winner_seat === 'draw' ? 'DRAW' : roomState.winner_seat.toUpperCase()) : 'NONE'}</strong>
          </p>
          <p className="outcome-reason">
            Reason: <code>{roomState.outcome_reason}</code>
          </p>
          <div className="outcome-actions">
            <button onClick={handleLeaveRoom} className="btn-primary">
              Play Again / Return
            </button>
          </div>
        </div>
      )}

      <div className="duel-workspace">
        {/* Left Player (Player 1) */}
        <div className="duel-lane">
          <div className="lane-header">Player 1 (Left)</div>
          <div className="duel-board-wrapper">
            {roomState?.player1_board ? (
              <TetrisBoard gameState={roomState.player1_board} />
            ) : (
              <div className="board-placeholder">
                <p>Initializing Board...</p>
              </div>
            )}
          </div>
          {renderBoardStats(roomState?.player1_board || null, "P1 Stats")}
        </div>

        {/* Right Player (Player 2) */}
        <div className="duel-lane">
          <div className="lane-header">Player 2 (Right)</div>
          <div className="duel-board-wrapper">
            {roomState?.player2_board ? (
              <TetrisBoard gameState={roomState.player2_board} />
            ) : (
              <div className="board-placeholder waiting-placeholder" data-testid="waiting-placeholder">
                <p>Waiting for Player 2...</p>
                <span className="pulse-loader"></span>
              </div>
            )}
          </div>
          {renderBoardStats(roomState?.player2_board || null, "P2 Stats")}
        </div>
      </div>

      {/* Interactive controls visible only for own seat when playing */}
      {isPlaying && seat && (
        <div className="duel-controls-panel">
          <p className="controls-label">Your Controls ({seat.toUpperCase()})</p>
          <div className="duel-buttons-grid">
            <button onClick={() => triggerAction('move', 'left')} className="btn-ctrl">Move Left</button>
            <button onClick={() => triggerAction('move', 'right')} className="btn-ctrl">Move Right</button>
            <button onClick={() => triggerAction('move', 'down')} className="btn-ctrl">Move Down</button>
            <button onClick={() => triggerAction('rotate', 'ccw')} className="btn-ctrl">Rotate CCW (Z)</button>
            <button onClick={() => triggerAction('rotate', 'cw')} className="btn-ctrl">Rotate CW (Up)</button>
            <button onClick={() => triggerAction('hold', null)} className="btn-ctrl">Hold Piece (C)</button>
          </div>
        </div>
      )}
    </div>
  );
};
