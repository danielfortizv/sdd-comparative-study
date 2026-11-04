from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_number: str
    account_type: str  # "checking" | "savings"
    account_name: str
    balance: float
    currency: str      # "USD"
    created_at: datetime

    model_config = {"from_attributes": True}


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: float = Field(..., gt=0, description="Transfer amount must be strictly positive")
    description: Optional[str] = None
    pin: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def validate_decimals(cls, v: float) -> float:
        # Check that amount has at most 2 decimal places
        rounded = round(v, 2)
        if abs(v - rounded) > 1e-6:
            raise ValueError("Transfer amount cannot have more than 2 decimal places")
        return rounded


class TransferResponse(BaseModel):
    id: int
    from_account_id: int
    to_account_id: int
    amount: float
    status: str  # "completed" | "mfa_required" | "failed"
    description: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    id: int
    account_id: int
    account_name: Optional[str] = None
    transfer_id: Optional[int] = None
    transaction_type: str  # "credit" | "debit"
    amount: float
    balance_after: float
    description: str
    reference: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MfaVerifyRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=10)


class MfaRequiredResponse(BaseModel):
    detail: str = "MFA_REQUIRED"
    message: str = "Security PIN required for transfers over $1,000"


class MfaVerifyResponse(BaseModel):
    valid: bool
    remaining_attempts: int
    locked: bool


class MfaStatusResponse(BaseModel):
    threshold: float
    locked: bool
    remaining_attempts: int
