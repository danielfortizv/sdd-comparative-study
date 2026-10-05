import uuid
import random
from typing import List, Optional, Dict
from .models import GameState, ActivePiece

TETROMINOES = {
    "I": [[1, 0], [1, 1], [1, 2], [1, 3]],
    "O": [[1, 1], [1, 2], [2, 1], [2, 2]],
    "T": [[1, 1], [2, 0], [2, 1], [2, 2]],
    "J": [[1, 0], [2, 0], [2, 1], [2, 2]],
    "L": [[1, 2], [2, 0], [2, 1], [2, 2]],
    "S": [[1, 1], [1, 2], [2, 0], [2, 1]],
    "Z": [[1, 0], [1, 1], [2, 1], [2, 2]],
}

class TetrisEngine:
    @staticmethod
    def create_empty_board() -> List[List[Optional[str]]]:
        return [[None for _ in range(10)] for _ in range(20)]

    @staticmethod
    def spawn_piece(board: List[List[Optional[str]]], force_piece_type: Optional[str] = None) -> tuple[ActivePiece, str]:
        """
        Spawns a random or forced piece at coordinate origin [0, 3].
        Returns (ActivePiece, status).
        If the newly spawned piece overlaps settled blocks, status becomes 'game_over'.
        """
        piece_type = force_piece_type or random.choice(list(TETROMINOES.keys()))
        local_coords = TETROMINOES[piece_type]
        origin = [0, 3]
        cells = [[origin[0] + r, origin[1] + c] for r, c in local_coords]
        
        # Check for overlap with settled blocks
        game_over = False
        for r, c in cells:
            if 0 <= r < 20 and 0 <= c < 10:
                if board[r][c] is not None:
                    game_over = True
            else:
                game_over = True
                
        active_piece = ActivePiece(type=piece_type, cells=cells, origin=origin)
        status = "game_over" if game_over else "playing"
        return active_piece, status

    @staticmethod
    def is_valid_position(board: List[List[Optional[str]]], cells: List[List[int]]) -> bool:
        for r, c in cells:
            if not (0 <= r < 20 and 0 <= c < 10):
                return False
            if board[r][c] is not None:
                return False
        return True

    @staticmethod
    def move_piece(board: List[List[Optional[str]]], active_piece: ActivePiece, direction: str) -> tuple[ActivePiece, bool]:
        """
        Attempts to move active piece.
        direction can be 'left', 'right', 'down'.
        Returns (new_active_piece, success).
        """
        origin = active_piece.origin
        if direction == "left":
            new_origin = [origin[0], origin[1] - 1]
        elif direction == "right":
            new_origin = [origin[0], origin[1] + 1]
        elif direction == "down":
            new_origin = [origin[0] + 1, origin[1]]
        else:
            return active_piece, False

        local_coords = TETROMINOES[active_piece.type]
        new_cells = [[new_origin[0] + r, new_origin[1] + c] for r, c in local_coords]
        
        if TetrisEngine.is_valid_position(board, new_cells):
            return ActivePiece(type=active_piece.type, cells=new_cells, origin=new_origin), True
        return active_piece, False

    @staticmethod
    def lock_piece(board: List[List[Optional[str]]], active_piece: ActivePiece) -> List[List[Optional[str]]]:
        """
        Locks the active piece cells onto the board matrix.
        """
        new_board = [row[:] for row in board]
        for r, c in active_piece.cells:
            if 0 <= r < 20 and 0 <= c < 10:
                new_board[r][c] = active_piece.type
        return new_board

    @staticmethod
    def clear_lines(board: List[List[Optional[str]]]) -> tuple[List[List[Optional[str]]], int]:
        """
        Identifies full rows (all 10 columns filled), clears them, shifts upper rows down, prepends empty rows.
        Returns (new_board, num_cleared).
        """
        non_full_rows = [row for row in board if any(cell is None for cell in row)]
        num_cleared = 20 - len(non_full_rows)
        new_board = [[None for _ in range(10)] for _ in range(num_cleared)] + non_full_rows
        return new_board, num_cleared


class GameSession:
    def __init__(self, session_id: str):
        self.id = session_id
        self.board = TetrisEngine.create_empty_board()
        self.status = "playing"
        self.next_pieces: List[str] = []
        self._spawn_next()

    def _spawn_next(self):
        force_type = self.next_pieces.pop(0) if self.next_pieces else None
        self.active_piece, self.status = TetrisEngine.spawn_piece(self.board, force_type)

    def step_down(self) -> bool:
        """
        Advances gravity down. If blocked, locks, clears, and spawns next piece.
        Returns True if successfully shifted down, False if locked.
        """
        if self.status == "game_over":
            return False

        new_piece, success = TetrisEngine.move_piece(self.board, self.active_piece, "down")
        if success:
            self.active_piece = new_piece
            return True
        else:
            self.board = TetrisEngine.lock_piece(self.board, self.active_piece)
            self.board, _ = TetrisEngine.clear_lines(self.board)
            self._spawn_next()
            return False

    def move(self, direction: str) -> bool:
        """
        Moves left/right/down.
        """
        if self.status == "game_over":
            return False

        if direction in ("left", "right"):
            new_piece, success = TetrisEngine.move_piece(self.board, self.active_piece, direction)
            if success:
                self.active_piece = new_piece
                return True
            return False
        elif direction == "down":
            return self.step_down()
        return False

    def reset(self):
        """
        Resets the session state.
        """
        self.board = TetrisEngine.create_empty_board()
        self.status = "playing"
        self.next_pieces = []
        self._spawn_next()

    def to_state(self) -> GameState:
        # Pydantic state model
        return GameState(
            id=self.id,
            board=self.board,
            active_piece=self.active_piece if self.status == "playing" else None,
            status=self.status
        )


class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, GameSession] = {}

    def create_session(self) -> GameSession:
        session_id = str(uuid.uuid4())
        session = GameSession(session_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[GameSession]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
