import random
from typing import List, Tuple, Dict
from app.models.game import TetrominoType

SHAPES: Dict[TetrominoType, List[Tuple[int, int]]] = {
    'I': [(0, 0), (0, 1), (0, 2), (0, 3)],
    'O': [(0, 0), (0, 1), (1, 0), (1, 1)],
    'T': [(0, 1), (1, 0), (1, 1), (1, 2)],
    'S': [(0, 1), (0, 2), (1, 0), (1, 1)],
    'Z': [(0, 0), (0, 1), (1, 1), (1, 2)],
    'J': [(0, 0), (1, 0), (1, 1), (1, 2)],
    'L': [(0, 2), (1, 0), (1, 1), (1, 2)],
}

def get_random_piece_type() -> TetrominoType:
    return random.choice(list(SHAPES.keys()))

def get_relative_cells(piece_type: TetrominoType) -> List[Tuple[int, int]]:
    return SHAPES[piece_type]
