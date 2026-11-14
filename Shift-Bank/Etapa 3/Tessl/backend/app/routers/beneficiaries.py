from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Beneficiary
from backend.app.schemas import BeneficiaryCreateRequest, BeneficiaryResponse
from backend.app.services.account_service import DEFAULT_USER_ID

router = APIRouter(prefix="/api/beneficiaries", tags=["Beneficiaries"])


@router.get("", response_model=List[BeneficiaryResponse], status_code=status.HTTP_200_OK)
def list_beneficiaries(db: Session = Depends(get_db)):
    """Retrieve all saved external beneficiaries for the authenticated user."""
    return (
        db.query(Beneficiary)
        .filter(Beneficiary.user_id == DEFAULT_USER_ID)
        .order_by(Beneficiary.name.asc())
        .all()
    )


@router.post("", response_model=BeneficiaryResponse, status_code=status.HTTP_201_CREATED)
def create_beneficiary(
    request: BeneficiaryCreateRequest,
    db: Session = Depends(get_db),
):
    """Add a new external beneficiary with format validation and audit logging."""
    from backend.app.services import audit_service

    beneficiary = Beneficiary(
        user_id=DEFAULT_USER_ID,
        name=request.name.strip(),
        routing_number=request.routing_number.strip(),
        account_number=request.account_number.strip(),
        bank_name=request.bank_name.strip(),
    )
    db.add(beneficiary)
    db.flush()

    audit_service.record_audit_event(
        db=db,
        event_type="beneficiary_created",
        status="SUCCESS",
        details={
            "beneficiary_id": beneficiary.id,
            "name": beneficiary.name,
            "bank_name": beneficiary.bank_name,
        },
        actor_id=DEFAULT_USER_ID,
    )

    db.commit()
    db.refresh(beneficiary)
    return beneficiary


@router.delete("/{beneficiary_id}", status_code=status.HTTP_200_OK)
def delete_beneficiary(
    beneficiary_id: int,
    db: Session = Depends(get_db),
):
    """Delete a saved beneficiary belonging to the authenticated user with audit logging."""
    from backend.app.services import audit_service

    beneficiary = (
        db.query(Beneficiary)
        .filter(Beneficiary.id == beneficiary_id, Beneficiary.user_id == DEFAULT_USER_ID)
        .first()
    )
    if not beneficiary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Beneficiary with ID {beneficiary_id} not found",
        )
    ben_name = beneficiary.name
    db.delete(beneficiary)

    audit_service.record_audit_event(
        db=db,
        event_type="beneficiary_deleted",
        status="SUCCESS",
        details={
            "beneficiary_id": beneficiary_id,
            "name": ben_name,
        },
        actor_id=DEFAULT_USER_ID,
    )

    db.commit()
    return {"status": "deleted", "id": beneficiary_id}
