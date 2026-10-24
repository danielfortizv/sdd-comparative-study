from pydantic import BaseModel
from typing import List
from ..domain.models import AccountType

def format_cents_to_usd(cents: int) -> str:
    """Format integer cents to exact USD string without floating point conversions."""
    dollars, remaining_cents = divmod(cents, 100)
    return f"${dollars:,}.{remaining_cents:02d}"

class AccountResponse(BaseModel):
    id: str
    nickname: str
    account_type: AccountType
    type: AccountType
    balance_cents: int
    balance_formatted: str

    @classmethod
    def from_row(cls, row) -> "AccountResponse":
        cents = row["balance_cents"]
        acc_type = AccountType(row["account_type"])
        return cls(
            id=row["id"],
            nickname=row["nickname"],
            account_type=acc_type,
            type=acc_type,
            balance_cents=cents,
            balance_formatted=format_cents_to_usd(cents),
        )

class AccountListResponse(BaseModel):
    accounts: List[AccountResponse]
