from datetime import datetime
from fastapi import APIRouter, status
from pydantic import BaseModel
from backend.app.services import crypto_service

router = APIRouter(prefix="/api/crypto", tags=["Cryptography"])


class PublicKeyResponse(BaseModel):
    key_id: str
    algorithm: str  # "RSA-OAEP-256"
    public_key: str  # PEM-encoded public key
    expires_at: datetime


@router.get(
    "/public-key",
    response_model=PublicKeyResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active RSA public key for client-to-server field encryption",
)
def get_public_key():
    """Returns the server's active RSA public key PEM, key_id, algorithm, and expiration timestamp."""
    return crypto_service.get_active_public_key()
