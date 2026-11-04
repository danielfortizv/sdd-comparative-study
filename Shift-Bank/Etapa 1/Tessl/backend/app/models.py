from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Alex Morgan")
    email = Column(String, unique=True, index=True, default="alex.morgan@shiftbank.mock")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    accounts = relationship("Account", back_populates="owner")
    mfa_state = relationship("MfaState", back_populates="user", uselist=False)


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_number = Column(String, unique=True, index=True, nullable=False)
    account_type = Column(String, nullable=False)  # "checking" | "savings"
    account_name = Column(String, nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    currency = Column(String, nullable=False, default="USD")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", order_by="desc(Transaction.created_at)")


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String, nullable=False, default="completed")  # "completed" | "mfa_required" | "failed"
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    transactions = relationship("Transaction", back_populates="transfer")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    transfer_id = Column(Integer, ForeignKey("transfers.id"), nullable=True)
    transaction_type = Column(String, nullable=False)  # "credit" | "debit"
    amount = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    account = relationship("Account", back_populates="transactions")
    transfer = relationship("Transfer", back_populates="transactions")


class MfaState(Base):
    __tablename__ = "mfa_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    failed_attempts = Column(Integer, nullable=False, default=0)
    is_locked = Column(Boolean, nullable=False, default=False)
    threshold = Column(Float, nullable=False, default=1000.00)

    user = relationship("User", back_populates="mfa_state")
