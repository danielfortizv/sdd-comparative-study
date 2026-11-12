import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.storage import clear_storage
from src.cache import response_cache


@pytest.fixture(autouse=True)
def run_around_tests():
    # Before each test, make sure storage and cache are reset
    clear_storage()
    response_cache.clear()
    yield
    # After each test, clean up storage and cache
    clear_storage()
    response_cache.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
