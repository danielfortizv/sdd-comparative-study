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
}

export interface MoveRequest {
  direction: 'left' | 'right' | 'down';
}
