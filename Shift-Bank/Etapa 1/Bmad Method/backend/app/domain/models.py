from enum import Enum
from pydantic import BaseModel
from typing import Optional

class AccountType(str, Enum):
    CHECKING = "CHECKING"
    SAVINGS = "SAVINGS"
    RESERVE = "RESERVE"

class TransferStatus(str, Enum):
    PENDING_MFA = "PENDING_MFA"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class TransferInitiationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    MFA_REQUIRED = "MFA_REQUIRED"

class MovementDirection(str, Enum):
    DEBIT = "DEBIT"
    CREDIT = "CREDIT"

class MfaStatus(str, Enum):
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    EXPIRED = "EXPIRED"
    EXHAUSTED = "EXHAUSTED"
    CANCELLED = "CANCELLED"
