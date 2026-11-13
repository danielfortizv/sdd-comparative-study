export type TetrominoType = 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L';

export type GameStatus = 'playing' | 'game_over';

export interface ActivePiece {
  type: TetrominoType;
  origin: [number, number]; // [row, col]
  cells: [number, number][]; // absolute coordinates on the board [row, col][]
  orientation: number;
}

export interface GameState {
  id: string;
  board: (string | null)[][]; // 20 rows of 10 columns
  active_piece: ActivePiece | null;
  status: GameStatus;
  score: number;
  total_lines: number;
  level: number;
  gravity_interval_ms: number;
  next_piece: TetrominoType;
  hold_piece: TetrominoType | null;
  can_hold: boolean;
  board_revision: number;
}

export type DuelRoomStatus = 'waiting' | 'playing' | 'finished';

export type SeatType = 'player1' | 'player2';

export type OutcomeReason =
  | 'topout-player1'
  | 'topout-player2'
  | 'simultaneous-topout'
  | 'forfeit-player1'
  | 'forfeit-player2'
  | 'waiting-peer-timeout'
  | 'waiting-aborted'
  | 'operational-abort';

export interface DuelRoomStateUpdate {
  room_id: string;
  room_revision: number;
  status: DuelRoomStatus;
  player1_board: GameState | null;
  player2_board: GameState | null;
  winner_seat: SeatType | 'draw' | null;
  outcome_reason: OutcomeReason | null;
}

export interface ClientHandshakeMessage {
  version: '1.0';
  type: 'handshake';
  payload: {
    room_id: string;
    client_id: string;
  };
}

export interface ClientActionMessage {
  version: '1.0';
  type: 'action';
  payload: {
    action_id: number;
    expected_revision: number;
    action_type: 'move' | 'hold' | 'rotate';
    direction: 'left' | 'right' | 'down' | 'cw' | 'ccw' | null;
  };
}

export interface ServerAckMessage {
  version: '1.0';
  type: 'ack';
  payload: {
    action_id: number;
    status: 'accepted' | 'noop' | 'rejected';
    reason: string;
    board_revision: number;
    room_revision: number;
    authoritative_board: GameState;
  };
}

export interface ServerStateUpdateMessage {
  version: '1.0';
  type: 'state_update';
  payload: DuelRoomStateUpdate;
}

export interface ServerHandshakeMessage {
  version: '1.0';
  type: 'handshake';
  payload: {
    seat: SeatType;
  };
}

export interface ServerErrorMessage {
  version: '1.0';
  type: 'error';
  payload: {
    error_code: number;
    message: string;
  };
}

export type DuelServerMessage =
  | ServerHandshakeMessage
  | ServerAckMessage
  | ServerStateUpdateMessage
  | ServerErrorMessage;
