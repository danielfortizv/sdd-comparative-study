from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


def _validate_decimal_amount(v: str) -> str:
    """Helper to validate that an amount string is a strictly positive Decimal with <= 2 decimal places."""
    try:
        val = Decimal(v)
        if val <= 0:
            raise ValueError("Amount must be greater than zero.")
        # Reject more than 2 decimal places in input string
        if "." in v and len(v.split(".")[1]) > 2:
            raise ValueError("Amount cannot have more than 2 decimal places.")
        return f"{val:.2f}"
    except (InvalidOperation, TypeError):
        raise ValueError("Amount must be a valid decimal string.")
    except ValueError as e:
        raise e


class AccountResponse(BaseModel):
    id: str
    name: str
    balance: str
    currency: str = "COP"
    version: int = 0


class TransferCreate(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount: str
    expected_versions: dict[str, int] = Field(default_factory=dict)

    @field_validator("amount")
    @classmethod
    def validate_amount_format(cls, v: str) -> str:
        return _validate_decimal_amount(v)


class TransferResponse(BaseModel):
    id: str
    source_account: str
    destination_account: str
    amount: str
    status: str
    created_at: str
    expires_at: str | None = None
    source_version: int | None = None
    destination_version: int | None = None
    source_account_id: str | None = None
    destination_account_id: str | None = None


class ConversionCreate(BaseModel):
    source_account_id: str
    destination_account_id: str
    source_amount: str
    expected_versions: dict[str, int] = Field(default_factory=dict)

    @field_validator("source_amount")
    @classmethod
    def validate_conversion_amount(cls, v: str) -> str:
        return _validate_decimal_amount(v)


class ConversionResponse(BaseModel):
    id: str
    source_account_id: str
    destination_account_id: str
    source_amount: str
    source_currency: str
    destination_amount: str
    destination_currency: str
    rate_numerator: int
    rate_denominator: int
    source_version: int
    destination_version: int


class MFACodeConfirm(BaseModel):
    code: str = ""
    mfa_code: str | None = None
    expected_versions: dict[str, int] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def normalize_code(cls, data):
        if isinstance(data, dict):
            code_val = data.get("code")
            mfa_val = data.get("mfa_code")
            if code_val and mfa_val and code_val != mfa_val:
                raise ValueError("Conflicting MFA code values provided in 'code' and 'mfa_code'.")
            if mfa_val and not code_val:
                data["code"] = mfa_val
        return data

    @field_validator("code")
    @classmethod
    def validate_code_format(cls, v: str) -> str:
        if not v or len(v) != 6 or not v.isdigit():
            raise ValueError("MFA code must be exactly 6 digits.")
        return v


class MFAConfirmResponse(BaseModel):
    id: str
    status: str
    message: str


class HistoryEntryResponse(BaseModel):
    id: str
    direction: str  # "incoming" or "outgoing"
    amount: str
    description: str
    date: str
    currency: str = "COP"
    counter_amount: str | None = None
    counter_currency: str | None = None
    rate_numerator: int | None = None
    rate_denominator: int | None = None


# ==============================================================================
# Stage 2 Models: Dynamic Limits (LIM-01..09, D-01, D-07)
# ==============================================================================

class LimitResponse(BaseModel):
    per_transfer_limit: str
    daily_limit: str
    current_daily_consumption: str
    remaining_daily_availability: str
    updated_at: str


class LimitUpdate(BaseModel):
    per_transfer_limit: str
    daily_limit: str

    @field_validator("per_transfer_limit", "daily_limit")
    @classmethod
    def validate_limit_amount(cls, v: str) -> str:
        return _validate_decimal_amount(v)


# ==============================================================================
# Stage 2 Models: External ACH Beneficiaries (ACH-01..03, D-08)
# ==============================================================================

class BeneficiaryCreate(BaseModel):
    name: str
    bank_name: str
    routing_number: str
    account_number: str

    @field_validator("name", "bank_name")
    @classmethod
    def validate_non_empty_str(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Field cannot be empty or whitespace only.")
        return s

    @field_validator("routing_number")
    @classmethod
    def validate_routing_number(cls, v: str) -> str:
        s = v.strip()
        if len(s) != 9 or not s.isdigit():
            raise ValueError("Routing number must be exactly 9 numeric digits.")
        return s

    @field_validator("account_number")
    @classmethod
    def validate_account_number(cls, v: str) -> str:
        s = v.strip()
        if not (4 <= len(s) <= 17) or not s.isdigit():
            raise ValueError("Account number must be between 4 and 17 numeric digits.")
        return s


class BeneficiaryResponse(BaseModel):
    id: str
    name: str
    bank_name: str
    routing_number: str
    account_number: str
    created_at: str


# ==============================================================================
# Stage 2 Models: ACH Transfers (ACH-04..10, D-06)
# ==============================================================================

class AchTransferCreate(BaseModel):
    source_account_id: str
    amount: str
    recipient_name: str
    bank_name: str
    routing_number: str
    account_number: str
    save_beneficiary: bool = False
    expected_versions: dict[str, int] = Field(default_factory=dict)

    @field_validator("amount")
    @classmethod
    def validate_ach_amount(cls, v: str) -> str:
        return _validate_decimal_amount(v)

    @field_validator("recipient_name", "bank_name")
    @classmethod
    def validate_ach_text(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Recipient and bank names cannot be empty.")
        return s

    @field_validator("routing_number")
    @classmethod
    def validate_ach_routing(cls, v: str) -> str:
        s = v.strip()
        if len(s) != 9 or not s.isdigit():
            raise ValueError("Routing number must be exactly 9 numeric digits.")
        return s

    @field_validator("account_number")
    @classmethod
    def validate_ach_account(cls, v: str) -> str:
        s = v.strip()
        if not (4 <= len(s) <= 17) or not s.isdigit():
            raise ValueError("Account number must be between 4 and 17 numeric digits.")
        return s


class AchTransferResponse(BaseModel):
    id: str
    transfer_type: str = "ACH"
    source_account: str
    recipient_name: str
    bank_name: str
    routing_number: str
    account_number: str
    amount: str
    status: str
    created_at: str
    expires_at: str | None = None
    currency: str = "COP"
    source_version: int = 0


# ==============================================================================
# Stage 2 Models: Recurring Schedules (REC-01..12, D-03, D-05, D-09)
# ==============================================================================

class RecurringScheduleCreate(BaseModel):
    transfer_type: Literal["INTERNAL", "ACH"]
    source_account_id: str
    amount: str
    frequency: Literal["DAILY", "WEEKLY", "MONTHLY"]
    start_date: str | None = None
    destination_account_id: str | None = None
    recipient_name: str | None = None
    bank_name: str | None = None
    routing_number: str | None = None
    account_number: str | None = None
    expected_versions: dict[str, int] = Field(default_factory=dict)

    @field_validator("amount")
    @classmethod
    def validate_sched_amount(cls, v: str) -> str:
        return _validate_decimal_amount(v)

    @field_validator("start_date")
    @classmethod
    def validate_start_date_format(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        try:
            datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            raise ValueError("start_date must be in YYYY-MM-DD format.")
        return s

    @model_validator(mode="after")
    def validate_transfer_targets(self):
        if self.transfer_type == "INTERNAL":
            if not self.destination_account_id or not self.destination_account_id.strip():
                raise ValueError("destination_account_id is required for INTERNAL recurring schedules.")
            if self.destination_account_id == self.source_account_id:
                raise ValueError("Source and destination accounts must be different.")
        elif self.transfer_type == "ACH":
            if not self.recipient_name or not self.recipient_name.strip():
                raise ValueError("recipient_name is required for ACH recurring schedules.")
            if not self.bank_name or not self.bank_name.strip():
                raise ValueError("bank_name is required for ACH recurring schedules.")
            if not self.routing_number or len(self.routing_number.strip()) != 9 or not self.routing_number.strip().isdigit():
                raise ValueError("routing_number must be exactly 9 numeric digits for ACH schedules.")
            if not self.account_number or not (4 <= len(self.account_number.strip()) <= 17) or not self.account_number.strip().isdigit():
                raise ValueError("account_number must be between 4 and 17 numeric digits for ACH schedules.")
        return self


class RecurringScheduleResponse(BaseModel):
    id: str
    transfer_type: str
    source_account_id: str
    source_account: str
    destination_display: str
    amount: str
    frequency: str
    status: str
    next_due_date: str
    last_executed_at: str | None = None
    mfa_expires_at: str | None = None
    created_at: str
    currency: str = "COP"


# ==============================================================================
# Stage 3 Models: Cryptographic Envelopes, Audit & Health (E3-ENC-01, E3-AUD-01, E3-DEP-01)
# ==============================================================================


class CryptographicEnvelope(BaseModel):
    """Client-originated encrypted payload wrapper."""
    encrypted_key: str
    iv: str
    ciphertext: str
    tag: str


class PublicKeyResponse(BaseModel):
    algorithm: str = "RSA-OAEP-256"
    format: str = "PEM"
    public_key: str
    key_id: str = "bank_pub_v1"


class AuditRecordResponse(BaseModel):
    id: int
    timestamp: str
    event_type: str
    actor_id: str
    resource_id: str | None = None
    payload_digest: str
    previous_hash: str
    record_hmac: str


class AuditVerificationResponse(BaseModel):
    is_valid: bool
    verified_records: int
    latest_sequence: int
    latest_hash: str
    details: str
    broken_sequence: int | None = None
    tail_truncation_detected: bool = False
    expected_head: str | None = None


class HealthResponse(BaseModel):
    status: str = "healthy"
    database: str = "connected"
    scheduler_active: bool = True
    crypto_keys_loaded: bool = True
    environment: str = "production"

