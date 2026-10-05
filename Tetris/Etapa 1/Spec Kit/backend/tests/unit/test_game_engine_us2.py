import pytest
from app.services.game_engine import clear_lines_in_board

def test_clear_lines_single_row():
    # Setup board with row 19 completely filled (non-zero) except empty above
    board = [[0] * 10 for _ in range(19)]
    board.append([3] * 10)  # Filled with purple blocks
    
    # Place a single block at row 18, col 5
    board[18][5] = 1
    
    cleared = clear_lines_in_board(board)
    assert cleared == 1
    # Check that row 19 is now the shifted row 18 (with the block at col 5)
    assert board[19][5] == 1
    # Check that other cells in row 19 are empty (since row 18 was mostly empty)
    assert board[19][4] == 0
    # Check that row 0 is completely empty
    assert board[0] == [0] * 10

def test_clear_lines_multiple_rows():
    board = [[0] * 10 for _ in range(18)]
    board.append([2] * 10)  # Row 18 filled
    board.append([2] * 10)  # Row 19 filled
    
    # Place block at row 17, col 1
    board[17][1] = 4
    
    cleared = clear_lines_in_board(board)
    assert cleared == 2
    # Row 19 should now be what row 17 was
    assert board[19][1] == 4
    # Top two rows (0 and 1) should be empty
    assert board[0] == [0] * 10
    assert board[1] == [0] * 10
