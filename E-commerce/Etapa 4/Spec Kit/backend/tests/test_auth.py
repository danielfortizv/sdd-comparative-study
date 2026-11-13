from fastapi import status


def test_register_user_success(client_identity):
    resp = client_identity.post(
        "/api/register", json={"identifier": "alice", "password": "supersecretpassword"}
    )
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.json()["message"] == "Account successfully registered."


def test_register_user_duplicate(client_identity):
    # First registration
    client_identity.post(
        "/api/register", json={"identifier": "alice", "password": "password123"}
    )
    # Duplicate registration
    resp = client_identity.post(
        "/api/register", json={"identifier": "alice", "password": "different_password"}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "already exists" in resp.json()["detail"]


def test_register_empty_fields(client_identity):
    resp = client_identity.post(
        "/api/register", json={"identifier": "", "password": ""}
    )
    assert resp.status_code == status.HTTP_400_BAD_REQUEST


def test_signin_user_success(client_identity):
    client_identity.post(
        "/api/register", json={"identifier": "alice", "password": "password123"}
    )
    resp = client_identity.post(
        "/api/signin", json={"identifier": "alice", "password": "password123"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "session_token" in resp.json()


def test_signin_user_invalid_credentials(client_identity):
    resp = client_identity.post(
        "/api/signin", json={"identifier": "invalid_user", "password": "wrong_password"}
    )
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_signout_user_success(client_identity):
    client_identity.post(
        "/api/register", json={"identifier": "alice", "password": "password123"}
    )
    login_resp = client_identity.post(
        "/api/signin", json={"identifier": "alice", "password": "password123"}
    )
    token = login_resp.json()["session_token"]
    
    # Sign out
    resp = client_identity.post(
        "/api/signout", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == status.HTTP_200_OK
    assert "successfully terminated" in resp.json()["message"]
