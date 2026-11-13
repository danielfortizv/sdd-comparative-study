import pytest
from fastapi import status

def test_register_and_signin(client):
    # 1. Test registration with valid identifier and password
    payload = {"identifier": "alice", "password": "supersecretpassword"}
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    assert response.json()["message"] == "Account successfully registered."

    # 2. Test registration with duplicate identifier
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "exists" in response.json()["error"]

    # 3. Test registration with incomplete payload
    response = client.post("/api/register", json={"identifier": "", "password": ""})
    assert response.status_code == status.HTTP_400_BAD_REQUEST

    # 4. Test sign-in with valid credentials
    signin_payload = {"identifier": "alice", "password": "supersecretpassword"}
    response = client.post("/api/signin", json=signin_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "session_token" in response.json()
    token = response.json()["session_token"]

    # 5. Test sign-in with invalid credentials
    bad_signin = {"identifier": "alice", "password": "wrongpassword"}
    response = client.post("/api/signin", json=bad_signin)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # 6. Test sign-out
    response = client.post("/api/signout", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "successfully terminated" in response.json()["message"]
