"""Esquemas Pydantic de request/response.

Los montos se transportan como cadenas decimales (decimal-string). Las respuestas exponen
solo nombres amigables, sin identificadores internos (Requisitos 2.1, 2.2, 3.5, 5.3).
"""

from typing import Literal

from pydantic import BaseModel, Field

AccountKind = Literal["checking", "savings"]


class AccountOut(BaseModel):
    name: str
    balance: str  # decimal-string


class AccountsResponse(BaseModel):
    accounts: list[AccountOut]


class CreateTransferRequest(BaseModel):
    from_: AccountKind = Field(alias="from")
    to: AccountKind
    amount: str  # decimal-string
    description: str = ""

    model_config = {"populate_by_name": True}


class CreateTransferResponse(BaseModel):
    status: str
    mfa_required: bool
    reference: str | None = None
    expires_at: str | None = None


class MfaRequest(BaseModel):
    code: str


class MfaResponse(BaseModel):
    status: str


class TransferDirection(BaseModel):
    from_: str = Field(serialization_alias="from")
    to: str

    model_config = {"populate_by_name": True}


class TransferHistoryItem(BaseModel):
    date: str
    direction: TransferDirection
    amount: str  # decimal-string
    description: str
    status: str


class TransfersHistoryResponse(BaseModel):
    transfers: list[TransferHistoryItem]


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody
