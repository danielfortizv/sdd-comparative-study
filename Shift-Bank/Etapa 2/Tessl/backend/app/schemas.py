import re
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
        rounded = round(v, 2)
        if abs(v - rounded) > 1e-6:
            raise ValueError("Transfer amount cannot have more than 2 decimal places")
        return rounded


class TransferResponse(BaseModel):
    id: int
    from_account_id: int
    to_account_id: Optional[int] = None
    amount: float
    status: str  # "completed" | "pending" | "settled" | "failed" | "mfa_required"
    description: Optional[str] = None
    transfer_type: Optional[str] = "internal"
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    created_at: datetime
    settled_at: Optional[datetime] = None

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
    status: Optional[str] = "completed"
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


# ==========================================
# Stage 2 Schemas
# ==========================================

class BeneficiaryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    routing_number: str = Field(..., min_length=9, max_length=9)
    account_number: str = Field(..., min_length=4, max_length=17)
    bank_name: str = Field(..., min_length=1)

    @field_validator("name", "bank_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace")
        return stripped

    @field_validator("routing_number")
    @classmethod
    def validate_routing(cls, v: str) -> str:
        if not re.fullmatch(r"^\d{9}$", v):
            raise ValueError("Routing number must be exactly 9 digits")
        return v

    @field_validator("account_number")
    @classmethod
    def validate_account(cls, v: str) -> str:
        if not re.fullmatch(r"^\d{4,17}$", v):
            raise ValueError("Account number must be between 4 and 17 digits")
        return v


class BeneficiaryResponse(BaseModel):
    id: int
    user_id: int
    name: str
    routing_number: str
    account_number: str
    bank_name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AchTransferRequest(BaseModel):
    from_account_id: int
    amount: float = Field(..., gt=0, description="Transfer amount must be strictly positive")
    description: Optional[str] = None
    pin: Optional[str] = None
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    save_beneficiary: Optional[bool] = False

    @field_validator("amount")
    @classmethod
    def validate_decimals(cls, v: float) -> float:
        rounded = round(v, 2)
        if abs(v - rounded) > 1e-6:
            raise ValueError("Transfer amount cannot have more than 2 decimal places")
        return rounded

    @field_validator("routing_number")
    @classmethod
    def validate_routing(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_str = v.strip()
            if v_str and not re.fullmatch(r"^\d{9}$", v_str):
                raise ValueError("Routing number must be exactly 9 digits")
            return v_str or None
        return None

    @field_validator("account_number")
    @classmethod
    def validate_account(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v_str = v.strip()
            if v_str and not re.fullmatch(r"^\d{4,17}$", v_str):
                raise ValueError("Account number must be between 4 and 17 digits")
            return v_str or None
        return None


class AchTransferResponse(BaseModel):
    id: int
    from_account_id: int
    beneficiary_id: Optional[int] = None
    recipient_name: str
    routing_number: str
    account_number: str
    bank_name: str
    amount: float
    status: str  # "pending" | "settled" | "failed"
    description: Optional[str] = None
    created_at: datetime
    settled_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class RecurringScheduleCreateRequest(BaseModel):
    transfer_type: str = Field(..., description="Must be 'internal' or 'ach'")
    from_account_id: int
    to_account_id: Optional[int] = None
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    amount: float = Field(..., gt=0, description="Amount must be strictly positive")
    frequency: str = Field(..., description="Must be 'daily', 'weekly', or 'monthly'")
    start_date: Optional[datetime] = None
    description: Optional[str] = None
    pin: Optional[str] = None

    @field_validator("transfer_type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("internal", "ach"):
            raise ValueError("transfer_type must be either 'internal' or 'ach'")
        return v

    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        if v not in ("daily", "weekly", "monthly"):
            raise ValueError("frequency must be 'daily', 'weekly', or 'monthly'")
        return v

    @field_validator("amount")
    @classmethod
    def validate_decimals(cls, v: float) -> float:
        rounded = round(v, 2)
        if abs(v - rounded) > 1e-6:
            raise ValueError("Amount cannot have more than 2 decimal places")
        return rounded


class RecurringScheduleResponse(BaseModel):
    id: int
    user_id: int
    transfer_type: str
    from_account_id: int
    to_account_id: Optional[int] = None
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[str] = None
    account_number: Optional[str] = None
    bank_name: Optional[str] = None
    amount: float
    frequency: str
    status: str  # "active" | "paused" | "cancelled"
    description: Optional[str] = None
    next_execution_date: datetime
    created_at: datetime
    last_executed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TransferLimitsResponse(BaseModel):
    per_transaction_limit: float
    daily_limit: float
    current_daily_total: float
    remaining_daily_limit: float

    model_config = {"from_attributes": True}


class TransferLimitsUpdateRequest(BaseModel):
    per_transaction_limit: float = Field(..., gt=0)
    daily_limit: float = Field(..., gt=0)

    @field_validator("per_transaction_limit", "daily_limit")
    @classmethod
    def validate_decimals(cls, v: float) -> float:
        rounded = round(v, 2)
        if abs(v - rounded) > 1e-6:
            raise ValueError("Limit amounts cannot have more than 2 decimal places")
        return rounded
