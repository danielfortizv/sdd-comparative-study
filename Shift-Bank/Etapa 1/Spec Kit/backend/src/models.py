from decimal import Decimal

from pydantic import BaseModel, field_validator


class AccountResponse(BaseModel):
    id: str
    name: str
    balance: str
    currency: str = "COP"

class TransferCreate(BaseModel):
    source_account_id: str
    destination_account_id: str
    amount: str

    @field_validator("amount")
    @classmethod
    def validate_amount_format(cls, v: str) -> str:
        try:
            val = Decimal(v)
            if val <= 0:
                raise ValueError("Amount must be greater than zero.")
            # Standardize formatting to 2 decimal places
            return f"{val:.2f}"
        except Exception as e:  # noqa: BLE001
            if isinstance(e, ValueError) and "greater than zero" in str(e):
                raise ValueError("Amount must be greater than zero.")
            raise ValueError("Amount must be a valid decimal string.")

class TransferResponse(BaseModel):
    id: str
    source_account: str
    destination_account: str
    amount: str
    status: str
    created_at: str
    expires_at: str | None = None

class MFACodeConfirm(BaseModel):
    code: str

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
    direction: str # "incoming" or "outgoing"
    amount: str
    description: str
    date: str
