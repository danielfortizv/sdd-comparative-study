from pydantic import BaseModel, Field
from typing import Optional
from .account import format_cents_to_usd

class TransferRequest(BaseModel):
    from_account_id: str = Field(..., description="Source account identifier")
    to_account_id: str = Field(..., description="Destination account identifier")
    amount_cents: int = Field(..., description="Transfer amount in integer cents")

class TransferItem(BaseModel):
    id: str
    source_account_id: str
    destination_account_id: str
    amount_cents: int
    amount_formatted: str
    status: str
    created_at: str

class AccountBalanceSummary(BaseModel):
    id: str
    balance_cents: int
    balance_formatted: str

class TransferResponse(BaseModel):
    transfer: TransferItem
    status: str
    source_account: Optional[AccountBalanceSummary] = None
    destination_account: Optional[AccountBalanceSummary] = None
