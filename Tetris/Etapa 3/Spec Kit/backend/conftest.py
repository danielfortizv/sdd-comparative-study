import sys
import os
import pytest

# Insert the parent directory of this conftest file (the backend folder itself) to sys.path
backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

@pytest.fixture(autouse=True)
def isolated_test_db(tmp_path, monkeypatch):
    """
    Ensures that every single test runs with its own completely isolated SQLite database.
    Prevents tests from mutating local files or interfering with each other.
    """
    db_file = tmp_path / "test-tetris.sqlite3"
    monkeypatch.setenv("TETRIS_DB_PATH", str(db_file))
    
    # Import and initialize database schema
    from app.services.database import init_db
    init_db()
    
    return db_file
