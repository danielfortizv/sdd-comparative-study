import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.storage import clear_storage


@pytest.fixture(autouse=True)
def run_around_tests():
    # Before each test, make sure storage is reset
    clear_storage()
    yield
    # After each test, clean up storage
    clear_storage()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
