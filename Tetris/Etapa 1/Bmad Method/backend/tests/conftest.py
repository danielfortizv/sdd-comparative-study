import sys
from pathlib import Path

# Ensure the app directory is available on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Returns a TestClient instance for the FastAPI application."""
    return TestClient(app)
