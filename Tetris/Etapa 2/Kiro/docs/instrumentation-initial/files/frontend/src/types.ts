// Types mirroring the backend API game-state payload.

export type Status = "playing" | "game_over";

export type PieceType = "I" | "O" | "T" | "S" | "Z" | "J" | "L";

export interface ActivePiece {
  type: PieceType;
  // [row, column] of the piece bounding-box origin.
  origin: [number, number];
  // Absolute occupied board cells as [row, column] pairs.
  cells: Array<[number, number]>;
}

export interface GameState {
  id: string;
  status: Status;
  // 20 rows x 10 columns; 0 = empty, 1..7 = settled block type codes.
  board: number[][];
  active_piece: ActivePiece | null;
}

export type Direction = "left" | "right" | "down";
