export interface Tetromino {
  type: 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L';
  cells: [number, number][]; // [row, col]
  origin: [number, number];   // [row, col]
}

export interface GameSession {
  id: string;
  board: number[][]; // 20 rows x 10 columns
  activePiece: Tetromino | null;
  status: 'playing' | 'game_over';
  score: number;
  total_lines: number;
  level: number;
  gravity_interval_ms: number;
  next_piece: string;
  hold_piece: string | null;
  can_hold: boolean;
}

export interface MoveRequest {
  direction: 'left' | 'right' | 'down';
}
