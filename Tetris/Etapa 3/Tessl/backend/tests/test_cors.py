import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import Settings
from pydantic import ValidationError

def test_cors_allowed_origin():
    client = TestClient(app)
    # Origin from the allowed list
    response = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"

def test_cors_rejected_origin():
    client = TestClient(app)
    # Origin NOT in the allowed list
    response = client.get("/", headers={"Origin": "http://untrusted-attacker.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers

def test_cors_wildcard_rejection():
    # Attempting to configure CORS with wildcard '*' must raise ValidationError
    with pytest.raises(ValidationError) as excinfo:
        Settings(cors_origins=["*"])
    
    assert "Wildcard CORS origin '*' is not allowed when credentials are enabled." in str(excinfo.value)

    # Test with extra spaces too
    with pytest.raises(ValidationError) as excinfo_space:
        Settings(cors_origins=[" * "])
    
    assert "Wildcard CORS origin '*' is not allowed when credentials are enabled." in str(excinfo_space.value)
