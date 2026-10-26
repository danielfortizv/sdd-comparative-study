export type TetrominoType = 'I' | 'O' | 'T' | 'S' | 'Z' | 'J' | 'L';

export type GameStatus = 'playing' | 'game_over';

export interface ActivePiece {
  type: TetrominoType;
  origin: [number, number]; // [row, col]
  cells: [number, number][]; // absolute coordinates on the board [row, col][]
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
}
