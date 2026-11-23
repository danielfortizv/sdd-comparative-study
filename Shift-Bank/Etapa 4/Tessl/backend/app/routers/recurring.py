from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.schemas import (
    RecurringScheduleCreateRequest,
    RecurringScheduleResponse,
    MfaRequiredResponse,
)
from backend.app.services import recurring_service
from backend.app.services.account_service import DEFAULT_USER_ID

router = APIRouter(prefix="/api/recurring", tags=["Recurring Payments"])


@router.get("", response_model=List[RecurringScheduleResponse], status_code=status.HTTP_200_OK)
def list_recurring_schedules(db: Session = Depends(get_db)):
    """Retrieve all recurring payment schedules configured by the user."""
    return recurring_service.get_user_schedules(db, DEFAULT_USER_ID)


@router.post(
    "",
    response_model=RecurringScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        428: {"model": MfaRequiredResponse, "description": "MFA Security PIN required"},
    },
)
def create_recurring_schedule(
    request: RecurringScheduleCreateRequest,
    db: Session = Depends(get_db),
):
    """Create a new recurring payment schedule for internal or ACH transfers."""
    return recurring_service.create_recurring_schedule(
        db=db,
        user_id=DEFAULT_USER_ID,
        request=request,
    )


@router.post("/{schedule_id}/pause", response_model=RecurringScheduleResponse, status_code=status.HTTP_200_OK)
def pause_recurring_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Pause an active recurring schedule."""
    return recurring_service.pause_schedule(db, schedule_id, DEFAULT_USER_ID)


@router.post("/{schedule_id}/resume", response_model=RecurringScheduleResponse, status_code=status.HTTP_200_OK)
def resume_recurring_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Resume a paused recurring schedule."""
    return recurring_service.resume_schedule(db, schedule_id, DEFAULT_USER_ID)


@router.post("/{schedule_id}/cancel", response_model=RecurringScheduleResponse, status_code=status.HTTP_200_OK)
def cancel_recurring_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
):
    """Cancel a recurring schedule permanently."""
    return recurring_service.cancel_schedule(db, schedule_id, DEFAULT_USER_ID)


@router.post("/process-due", status_code=status.HTTP_200_OK)
def process_due_recurring_payments(db: Session = Depends(get_db)):
    """Trigger processing of all due recurring payments immediately (testing & simulation)."""
    results = recurring_service.execute_due_recurring_schedules(db)
    return {"processed_count": len(results), "executions": results}
