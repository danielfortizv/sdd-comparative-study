from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    event,
    DDL,
)
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator
from backend.app.database import Base


class SqliteDecimal(TypeDecorator):
    """SQLAlchemy TypeDecorator that stores Decimal as exact string in SQLite and returns Decimal."""
    impl = String(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class SqliteExactDecimal(TypeDecorator):
    """SQLAlchemy TypeDecorator that stores Decimal as exact string in SQLite without 2-decimal truncation."""
    impl = String(64)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(Decimal(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return Decimal(str(value))


class EncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator that encrypts sensitive data with AES-256-GCM at rest."""
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        from backend.app.services.crypto_service import encrypt_at_rest
        return encrypt_at_rest(str(value))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        from backend.app.services.crypto_service import decrypt_at_rest
        return decrypt_at_rest(value)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, default="Alex Morgan")
    email = Column(String, unique=True, index=True, default="alex.morgan@shiftbank.mock")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    accounts = relationship("Account", back_populates="owner")
    mfa_state = relationship("MfaState", back_populates="user", uselist=False)
    beneficiaries = relationship("Beneficiary", back_populates="user", cascade="all, delete-orphan")
    recurring_schedules = relationship("RecurringSchedule", back_populates="user", cascade="all, delete-orphan")
    transfer_limits = relationship("TransferLimit", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_number = Column(String, unique=True, index=True, nullable=False)
    account_type = Column(String, nullable=False)  # "checking" | "savings"
    account_name = Column(String, nullable=False)
    balance = Column(SqliteDecimal, nullable=False, default=Decimal("0.00"), server_default="0.00")
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    version = Column(Integer, nullable=False, default=1, server_default="1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account", order_by="desc(Transaction.created_at)")


class Beneficiary(Base):
    __tablename__ = "beneficiaries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    routing_number = Column(EncryptedString, nullable=False)
    account_number = Column(EncryptedString, nullable=False)
    bank_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="beneficiaries")


class Transfer(Base):
    __tablename__ = "transfers"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(String(64), unique=True, nullable=True, index=True)
    transfer_type = Column(String, nullable=False, default="internal", server_default="internal")  # "internal" | "ach"
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.id"), nullable=True)
    recipient_name = Column(String, nullable=True)
    routing_number = Column(EncryptedString, nullable=True)
    account_number = Column(EncryptedString, nullable=True)
    bank_name = Column(String, nullable=True)
    amount = Column(SqliteDecimal, nullable=False)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    from_account_version = Column(Integer, nullable=True)
    to_account_version = Column(Integer, nullable=True)
    status = Column(String, nullable=False, default="completed", server_default="completed")  # "completed" | "pending" | "settled" | "failed" | "mfa_required"
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    settled_at = Column(DateTime, nullable=True)

    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    beneficiary = relationship("Beneficiary", foreign_keys=[beneficiary_id])
    transactions = relationship("Transaction", back_populates="transfer")


class Conversion(Base):
    __tablename__ = "conversions"

    id = Column(Integer, primary_key=True, index=True)
    operation_id = Column(String(64), unique=True, nullable=False, index=True)
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    source_currency = Column(String(3), nullable=False)
    destination_currency = Column(String(3), nullable=False)
    source_amount = Column(SqliteDecimal, nullable=False)
    destination_amount = Column(SqliteDecimal, nullable=False)
    exchange_rate_display = Column(SqliteExactDecimal, nullable=False)
    rate_numerator = Column(Integer, nullable=False)
    rate_denominator = Column(Integer, nullable=False)
    rate_version = Column(String(32), nullable=False, default="v1.0-simulated")
    rounding_residual = Column(SqliteExactDecimal, nullable=False, default=Decimal("0.00"))
    from_account_version = Column(Integer, nullable=False)
    to_account_version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="completed")
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    transactions = relationship("Transaction", back_populates="conversion")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    transfer_id = Column(Integer, ForeignKey("transfers.id"), nullable=True)
    conversion_id = Column(Integer, ForeignKey("conversions.id"), nullable=True)
    transaction_type = Column(String, nullable=False)  # "credit" | "debit"
    amount = Column(SqliteDecimal, nullable=False)
    balance_after = Column(SqliteDecimal, nullable=False)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    description = Column(String, nullable=False)
    reference = Column(String, nullable=True)
    source_amount = Column(SqliteDecimal, nullable=True)
    source_currency = Column(String(3), nullable=True)
    destination_amount = Column(SqliteDecimal, nullable=True)
    destination_currency = Column(String(3), nullable=True)
    exchange_rate_display = Column(SqliteExactDecimal, nullable=True)
    status = Column(String, nullable=False, default="completed", server_default="completed")  # "completed" | "pending" | "failed"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    account = relationship("Account", back_populates="transactions")
    transfer = relationship("Transfer", back_populates="transactions")
    conversion = relationship("Conversion", back_populates="transactions")


class MfaState(Base):
    __tablename__ = "mfa_states"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    failed_attempts = Column(Integer, nullable=False, default=0)
    is_locked = Column(Boolean, nullable=False, default=False)
    threshold = Column(SqliteDecimal, nullable=False, default=Decimal("1000.00"))

    user = relationship("User", back_populates="mfa_state")


class RecurringSchedule(Base):
    __tablename__ = "recurring_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transfer_type = Column(String, nullable=False, default="internal", server_default="internal")  # "internal" | "ach"
    from_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=False)
    to_account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    beneficiary_id = Column(Integer, ForeignKey("beneficiaries.id"), nullable=True)
    recipient_name = Column(String, nullable=True)
    routing_number = Column(EncryptedString, nullable=True)
    account_number = Column(EncryptedString, nullable=True)
    bank_name = Column(String, nullable=True)
    amount = Column(SqliteDecimal, nullable=False)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    frequency = Column(String, nullable=False)  # "daily" | "weekly" | "monthly"
    status = Column(String, nullable=False, default="active", server_default="active")  # "active" | "paused" | "cancelled"
    description = Column(String, nullable=True)
    next_execution_date = Column(DateTime, nullable=False)
    last_executed_at = Column(DateTime, nullable=True)
    failure_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="recurring_schedules")
    from_account = relationship("Account", foreign_keys=[from_account_id])
    to_account = relationship("Account", foreign_keys=[to_account_id])
    beneficiary = relationship("Beneficiary", foreign_keys=[beneficiary_id])


class TransferLimit(Base):
    __tablename__ = "transfer_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    per_transaction_limit = Column(SqliteDecimal, nullable=False, default=Decimal("5000.00"))
    daily_limit = Column(SqliteDecimal, nullable=False, default=Decimal("10000.00"))

    user = relationship("User", back_populates="transfer_limits")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    event_id = Column(String, unique=True, nullable=False, index=True)
    timestamp = Column(String(40), nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    event_type = Column(String, nullable=False, index=True)
    actor_id = Column(Integer, nullable=True)
    status = Column(String, nullable=False)  # "SUCCESS" | "FAILURE"
    details = Column(String, nullable=False, default="{}")  # Canonical JSON
    previous_hash = Column(String(64), nullable=False)
    current_hash = Column(String(64), nullable=False, index=True)
    signature = Column(String(64), nullable=False)


class DomainEvent(Base):
    __tablename__ = "domain_events"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    aggregate_id = Column(String(64), nullable=False, index=True)
    aggregate_version = Column(Integer, nullable=False, default=1)
    account_ids = Column(String(128), nullable=False)  # JSON or comma-separated list of affected account IDs
    payload = Column(String, nullable=False, default="{}")  # Canonical JSON payload
    correlation_id = Column(String(64), nullable=True)
    idempotency_key = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class ProjectionCheckpoint(Base):
    __tablename__ = "projection_checkpoints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    projection_name = Column(String(64), unique=True, nullable=False, index=True)
    last_applied_event_id = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    idempotency_key = Column(String(64), unique=True, nullable=False, index=True)
    operation_type = Column(String(32), nullable=False)  # "transfer" | "conversion" | "ach"
    operation_id = Column(String(64), nullable=False)
    request_fingerprint = Column(String(64), nullable=False)  # SHA-256 of canonical business parameters
    response_payload = Column(String, nullable=False)  # JSON string of committed response
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


# Trigger DDL for SQLite to prevent UPDATE and DELETE on audit_logs
event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
        BEFORE UPDATE ON audit_logs
        BEGIN
            SELECT RAISE(FAIL, 'UPDATE operations are strictly forbidden on audit_logs ledger');
        END;
        """
    ),
)

event.listen(
    AuditLog.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
        BEFORE DELETE ON audit_logs
        BEGIN
            SELECT RAISE(FAIL, 'DELETE operations are strictly forbidden on audit_logs ledger');
        END;
        """
    ),
)

@event.listens_for(AuditLog, "before_update")
def receive_before_update(mapper, connection, target):
    raise RuntimeError("UPDATE operations are strictly forbidden on audit_logs ledger")

@event.listens_for(AuditLog, "before_delete")
def receive_before_delete(mapper, connection, target):
    raise RuntimeError("DELETE operations are strictly forbidden on audit_logs ledger")


# Trigger DDL for SQLite to prevent UPDATE and DELETE on domain_events
event.listen(
    DomainEvent.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_domain_event_update
        BEFORE UPDATE ON domain_events
        BEGIN
            SELECT RAISE(FAIL, 'UPDATE operations are strictly forbidden on domain_events store');
        END;
        """
    ),
)

event.listen(
    DomainEvent.__table__,
    "after_create",
    DDL(
        """
        CREATE TRIGGER IF NOT EXISTS prevent_domain_event_delete
        BEFORE DELETE ON domain_events
        BEGIN
            SELECT RAISE(FAIL, 'DELETE operations are strictly forbidden on domain_events store');
        END;
        """
    ),
)

@event.listens_for(DomainEvent, "before_update")
def receive_domain_event_before_update(mapper, connection, target):
    raise RuntimeError("UPDATE operations are strictly forbidden on domain_events store")

@event.listens_for(DomainEvent, "before_delete")
def receive_domain_event_before_delete(mapper, connection, target):
    raise RuntimeError("DELETE operations are strictly forbidden on domain_events store")
