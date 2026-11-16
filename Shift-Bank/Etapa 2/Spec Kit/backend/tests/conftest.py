import os
import sys
import pytest

# Ensure backend/src is in sys.path
backend_src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if backend_src not in sys.path:
    sys.path.insert(0, backend_src)

# Configure isolated test database path to strictly prevent modifying backend/shift_bank.db (D-02, F-10)
TEST_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "test_shift_bank.db"))
os.environ["TEST_DB_PATH"] = TEST_DB_PATH
os.environ["ENABLE_TEST_ENDPOINTS"] = "true"

import database


@pytest.fixture(scope="session", autouse=True)
def isolated_test_database():
    """Session fixture ensuring tests run strictly against an isolated database and clean up afterward."""
    os.environ["TEST_DB_PATH"] = TEST_DB_PATH
    os.environ["ENABLE_TEST_ENDPOINTS"] = "true"
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass
    database.init_db(TEST_DB_PATH)
    yield
    # Teardown: clean up test database file
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except OSError:
            pass


@pytest.fixture(autouse=True)
def reset_limits_to_defaults():
    """Resets user_mock_001 limits to default COP 5M / COP 10M before every test function (D-01).
    Ensures complete isolation between test modules.
    """
    conn = database.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE limits
            SET per_transfer_limit = '5000000.00', daily_limit = '10000000.00'
            WHERE user_id = 'user_mock_001';
        """)
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()
    yield
