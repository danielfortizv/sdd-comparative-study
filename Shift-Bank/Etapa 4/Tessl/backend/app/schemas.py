import re
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional, List, Union, Dict, Any
from typing_extensions import Annotated
from pydantic import BaseModel, Field, PlainSerializer, field_validator, model_validator


def serialize_monetary_amount(x: Any) -> Optional[str]:
    """Serialize monetary amount to canonical exact string with 2 decimal places."""
    if x is None:
        return None
    d = Decimal(str(x))
    return f"{d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"


def serialize_exact_decimal(x: Any) -> Optional[str]:
    """Serialize decimal to exact string without 2-decimal truncation (for rates and residuals)."""
    if x is None:
        return None
    d = Decimal(str(x))
    return f"{d:f}"


MonetaryAmount = Annotated[
    Decimal,
    PlainSerializer(
        serialize_monetary_amount,
        return_type=str,
        when_used="json-unless-none",
    ),
]

ExactDecimal = Annotated[
    Decimal,
    PlainSerializer(
        serialize_exact_decimal,
        return_type=str,
        when_used="json-unless-none",
    ),
]

DecimalFloat = MonetaryAmount


def parse_and_validate_monetary_amount(v: Any) -> Decimal:
    """Validate and quantize monetary amount to exactly 2 decimal places."""
    if v is None:
        raise ValueError("Amount is required")
    try:
        d = Decimal(str(v))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Invalid monetary amount")
    if d <= Decimal("0.00"):
        raise ValueError("Amount must be strictly positive")
    if d.as_tuple().exponent < -2:
        raise ValueError("Amount cannot have more than 2 decimal places")
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_number: str
    account_type: str  # "checking" | "savings"
    account_name: str
    balance: MonetaryAmount
    currency: str      # "USD" | "EUR" | "GBP"
    version: int = 1
    created_at: datetime

    model_config = {"from_attributes": True}


class TransferRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    amount: Decimal = Field(..., gt=0, description="Transfer amount must be strictly positive")
    expected_from_version: int = Field(..., ge=0, description="Expected version of source account for optimistic concurrency [NEW D-14]")
    expected_to_version: int = Field(..., ge=0, description="Expected version of destination account for optimistic concurrency [NEW D-14]")
    description: Optional[str] = None
    pin: Optional[str] = None

    @field_validator("amount", mode="before")
    @classmethod
    def validate_decimals(cls, v: Any) -> Decimal:
        return parse_and_validate_monetary_amount(v)


class TransferResponse(BaseModel):
    id: int
    operation_id: Optional[str] = None
    from_account_id: int
    to_account_id: Optional[int] = None
    amount: MonetaryAmount
    currency: Optional[str] = "USD"
    from_account_version: Optional[int] = None
    to_account_version: Optional[int] = None
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


class ConversionRequest(BaseModel):
    from_account_id: int
    to_account_id: int
    source_amount: Decimal = Field(..., gt=0, description="Source amount must be strictly positive")
    expected_from_version: int = Field(..., ge=0, description="Expected version of source account")
    expected_to_version: int = Field(..., ge=0, description="Expected version of destination account")
    description: Optional[str] = None
    pin: Optional[str] = None

    @field_validator("source_amount", mode="before")
    @classmethod
    def validate_source_amount(cls, v: Any) -> Decimal:
        return parse_and_validate_monetary_amount(v)


class ConversionResponse(BaseModel):
    id: int
    operation_id: str
    from_account_id: int
    to_account_id: int
    source_currency: str
    destination_currency: str
    source_amount: MonetaryAmount
    destination_amount: MonetaryAmount
    exchange_rate_display: ExactDecimal
    rate_numerator: int
    rate_denominator: int
    rate_version: str = "v1.0-simulated"
    rounding_residual: ExactDecimal = Decimal("0.00")
    from_account_version: int
    to_account_version: int
    status: str = "completed"
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    id: int
    account_id: int
    account_name: Optional[str] = None
    transfer_id: Optional[int] = None
    conversion_id: Optional[int] = None
    transaction_type: str  # "credit" | "debit"
    amount: MonetaryAmount
    balance_after: MonetaryAmount
    currency: str = "USD"
    description: str
    reference: Optional[str] = None
    source_amount: Optional[MonetaryAmount] = None
    source_currency: Optional[str] = None
    destination_amount: Optional[MonetaryAmount] = None
    destination_currency: Optional[str] = None
    exchange_rate_display: Optional[ExactDecimal] = None
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
    threshold: MonetaryAmount = Field(default=Decimal("1000.00"))
    locked: bool
    remaining_attempts: int


# ==========================================
# Stage 3 Cryptographic Schemas
# ==========================================

class EncryptedEnvelope(BaseModel):
    ciphertext: str       # Base64-encoded encrypted data
    encrypted_key: str    # Base64-encoded session key encrypted with server public key
    iv: str               # Base64-encoded initialization vector / nonce (96-bit for AES-GCM)
    tag: str              # Base64-encoded authentication tag (128-bit)
    key_id: str           # Identifier of the server public key used


class EncryptedFieldPayload(BaseModel):
    __encrypted__: bool = True
    key_id: str
    encrypted_key: str
    iv: str
    ciphertext: str
    tag: str


# ==========================================
# Stage 2 Schemas
# ==========================================

class BeneficiaryCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    routing_number: Union[str, EncryptedFieldPayload, Dict[str, Any]]
    account_number: Union[str, EncryptedFieldPayload, Dict[str, Any]]
    bank_name: str = Field(..., min_length=1)

    @model_validator(mode="before")
    @classmethod
    def decrypt_sensitive_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            from backend.app.services.crypto_service import decrypt_field_if_needed
            if "routing_number" in data and data["routing_number"] is not None:
                data["routing_number"] = decrypt_field_if_needed(data["routing_number"])
            if "account_number" in data and data["account_number"] is not None:
                data["account_number"] = decrypt_field_if_needed(data["account_number"])
        return data

    @field_validator("name", "bank_name")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field cannot be empty or whitespace")
        return stripped

    @field_validator("routing_number")
    @classmethod
    def validate_routing(cls, v: Any) -> str:
        v_str = str(v).strip()
        if not re.fullmatch(r"^\d{9}$", v_str):
            raise ValueError("Routing number must be exactly 9 digits")
        return v_str

    @field_validator("account_number")
    @classmethod
    def validate_account(cls, v: Any) -> str:
        v_str = str(v).strip()
        if not re.fullmatch(r"^\d{4,17}$", v_str):
            raise ValueError("Account number must be between 4 and 17 digits")
        return v_str


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
    amount: Decimal = Field(..., gt=0, description="Transfer amount must be strictly positive")
    expected_from_version: int = Field(..., ge=0, description="Expected version of source account for optimistic concurrency [NEW D-14]")
    description: Optional[str] = None
    pin: Optional[str] = None
    beneficiary_id: Optional[int] = None
    recipient_name: Optional[str] = None
    routing_number: Optional[Union[str, EncryptedFieldPayload, Dict[str, Any]]] = None
    account_number: Optional[Union[str, EncryptedFieldPayload, Dict[str, Any]]] = None
    bank_name: Optional[str] = None
    save_beneficiary: Optional[bool] = False

    @model_validator(mode="before")
    @classmethod
    def decrypt_sensitive_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            from backend.app.services.crypto_service import decrypt_field_if_needed
            if "routing_number" in data and data["routing_number"] is not None:
                data["routing_number"] = decrypt_field_if_needed(data["routing_number"])
            if "account_number" in data and data["account_number"] is not None:
                data["account_number"] = decrypt_field_if_needed(data["account_number"])
        return data

    @field_validator("amount", mode="before")
    @classmethod
    def validate_decimals(cls, v: Any) -> Decimal:
        return parse_and_validate_monetary_amount(v)

    @field_validator("routing_number")
    @classmethod
    def validate_routing(cls, v: Optional[Any]) -> Optional[str]:
        if v is not None:
            v_str = str(v).strip()
            if v_str and not re.fullmatch(r"^\d{9}$", v_str):
                raise ValueError("Routing number must be exactly 9 digits")
            return v_str or None
        return None

    @field_validator("account_number")
    @classmethod
    def validate_account(cls, v: Optional[Any]) -> Optional[str]:
        if v is not None:
            v_str = str(v).strip()
            if v_str and not re.fullmatch(r"^\d{4,17}$", v_str):
                raise ValueError("Account number must be between 4 and 17 digits")
            return v_str or None
        return None


class AchTransferResponse(BaseModel):
    id: int
    operation_id: Optional[str] = None
    from_account_id: int
    from_account_version: Optional[int] = None
    beneficiary_id: Optional[int] = None
    recipient_name: str
    routing_number: str
    account_number: str
    bank_name: str
    amount: MonetaryAmount
    currency: str = "USD"
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
    routing_number: Optional[Union[str, EncryptedFieldPayload, Dict[str, Any]]] = None
    account_number: Optional[Union[str, EncryptedFieldPayload, Dict[str, Any]]] = None
    bank_name: Optional[str] = None
    amount: Decimal = Field(..., gt=0, description="Amount must be strictly positive")
    frequency: str = Field(..., description="Must be 'daily', 'weekly', or 'monthly'")
    start_date: Optional[datetime] = None
    description: Optional[str] = None
    pin: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def decrypt_sensitive_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            from backend.app.services.crypto_service import decrypt_field_if_needed
            if "routing_number" in data and data["routing_number"] is not None:
                data["routing_number"] = decrypt_field_if_needed(data["routing_number"])
            if "account_number" in data and data["account_number"] is not None:
                data["account_number"] = decrypt_field_if_needed(data["account_number"])
        return data

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

    @field_validator("amount", mode="before")
    @classmethod
    def validate_decimals(cls, v: Any) -> Decimal:
        return parse_and_validate_monetary_amount(v)


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
    amount: MonetaryAmount
    currency: str = "USD"
    frequency: str
    status: str  # "active" | "paused" | "cancelled"
    description: Optional[str] = None
    next_execution_date: datetime
    created_at: datetime
    last_executed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class TransferLimitsResponse(BaseModel):
    per_transaction_limit: MonetaryAmount
    daily_limit: MonetaryAmount
    current_daily_total: MonetaryAmount
    remaining_daily_limit: MonetaryAmount
    reference_currency: str = "USD"

    model_config = {"from_attributes": True}


class TransferLimitsUpdateRequest(BaseModel):
    per_transaction_limit: Decimal = Field(..., gt=0)
    daily_limit: Decimal = Field(..., gt=0)

    @field_validator("per_transaction_limit", "daily_limit", mode="before")
    @classmethod
    def validate_decimals(cls, v: Any) -> Decimal:
        return parse_and_validate_monetary_amount(v)


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: Optional[str] = None
