import os
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.services import audit_service

router = APIRouter(prefix="/api/audit", tags=["Audit"])


class AuditVerificationResponse(BaseModel):
    valid: bool
    total_records: int
    tampered_entry_id: Optional[int] = None
    reason: Optional[str] = None  # "hash_mismatch" | "signature_mismatch" | "broken_chain"


@router.get(
    "/verify",
    response_model=AuditVerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Cryptographically verify audit ledger chain and signatures",
)
def verify_audit_ledger(
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    db: Session = Depends(get_db),
):
    """Verify integrity of the audit ledger from genesis to head.

    Protected endpoint: requires X-Admin-Key header matching ADMIN_SECRET_KEY.
    """
    admin_key = os.getenv("ADMIN_SECRET_KEY")
    if not admin_key and os.getenv("TESTING", "false").lower() == "true":
        admin_key = "test_admin_secret_key_2026"

    if not admin_key or x_admin_key != admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="FORBIDDEN_ADMIN_ACCESS_REQUIRED",
        )

    result = audit_service.verify_audit_chain(db)
    return AuditVerificationResponse(**result)
