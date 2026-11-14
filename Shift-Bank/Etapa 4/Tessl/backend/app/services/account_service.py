from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models import User, Account, Transaction, MfaState, TransferLimit


DEFAULT_USER_ID = 1


def seed_initial_data(db: Session) -> User:
    """Seed initial mock user, accounts (USD, EUR, GBP), and sample transactions if not already populated."""
    user = db.query(User).filter(User.id == DEFAULT_USER_ID).first()
    if not user:
        # Create mock user
        user = User(
            id=DEFAULT_USER_ID,
            name="Alex Morgan",
            email="alex.morgan@shiftbank.mock",
        )
        db.add(user)
        db.flush()

    # Create initial MFA state if missing
    mfa_state = db.query(MfaState).filter(MfaState.user_id == user.id).first()
    if not mfa_state:
        mfa_state = MfaState(
            user_id=user.id,
            failed_attempts=0,
            is_locked=False,
            threshold=Decimal("1000.00"),
        )
        db.add(mfa_state)

    # Create default transfer limits if missing
    limits = db.query(TransferLimit).filter(TransferLimit.user_id == user.id).first()
    if not limits:
        limits = TransferLimit(
            user_id=user.id,
            per_transaction_limit=Decimal("5000.00"),
            daily_limit=Decimal("10000.00"),
        )
        db.add(limits)

    now = datetime.now(timezone.utc)

    # Account 1: Primary Checking ($2,500.00 USD)
    checking = db.query(Account).filter(Account.account_number == "CHK-1001").first()
    if not checking:
        checking = Account(
            user_id=user.id,
            account_number="CHK-1001",
            account_type="checking",
            account_name="Primary Checking",
            balance=Decimal("2500.00"),
            currency="USD",
            version=1,
            created_at=now - timedelta(days=30),
        )
        db.add(checking)
        db.flush()

        # Initial transactions for Checking
        tx1 = Transaction(
            account_id=checking.id,
            transaction_type="credit",
            amount=Decimal("3000.00"),
            balance_after=Decimal("3000.00"),
            currency="USD",
            description="Payroll Direct Deposit - Shift Tech Inc",
            reference="PAY-88210",
            created_at=now - timedelta(days=15),
        )
        tx2 = Transaction(
            account_id=checking.id,
            transaction_type="debit",
            amount=Decimal("500.00"),
            balance_after=Decimal("2500.00"),
            currency="USD",
            description="Electric & Water Utility Payment",
            reference="UTL-44912",
            created_at=now - timedelta(days=5),
        )
        db.add_all([tx1, tx2])

    # Account 2: Standard Savings ($10,000.00 USD)
    savings = db.query(Account).filter(Account.account_number == "SAV-2001").first()
    if not savings:
        savings = Account(
            user_id=user.id,
            account_number="SAV-2001",
            account_type="savings",
            account_name="Standard Savings",
            balance=Decimal("10000.00"),
            currency="USD",
            version=1,
            created_at=now - timedelta(days=60),
        )
        db.add(savings)
        db.flush()

        # Initial transaction for Savings
        tx3 = Transaction(
            account_id=savings.id,
            transaction_type="credit",
            amount=Decimal("10000.00"),
            balance_after=Decimal("10000.00"),
            currency="USD",
            description="Initial Savings Account Funding",
            reference="DEP-10001",
            created_at=now - timedelta(days=45),
        )
        db.add(tx3)

    # Account 3: Euro Account (€0.00 EUR) - Stage 4 (D-02)
    euro_acc = db.query(Account).filter(Account.account_number == "EUR-3001").first()
    if not euro_acc:
        euro_acc = Account(
            user_id=user.id,
            account_number="EUR-3001",
            account_type="checking",
            account_name="Euro Account",
            balance=Decimal("0.00"),
            currency="EUR",
            version=1,
            created_at=now - timedelta(days=10),
        )
        db.add(euro_acc)

    # Account 4: British Pound Account (£0.00 GBP) - Stage 4 (D-02)
    gbp_acc = db.query(Account).filter(Account.account_number == "GBP-4001").first()
    if not gbp_acc:
        gbp_acc = Account(
            user_id=user.id,
            account_number="GBP-4001",
            account_type="savings",
            account_name="British Pound Account",
            balance=Decimal("0.00"),
            currency="GBP",
            version=1,
            created_at=now - timedelta(days=10),
        )
        db.add(gbp_acc)

    db.commit()
    db.refresh(user)
    return user


def get_user_accounts(db: Session, user_id: int = DEFAULT_USER_ID) -> List[Account]:
    """Retrieve all accounts for the authenticated user from CQRS read projections."""
    accounts = (
        db.query(Account)
        .filter(Account.user_id == user_id)
        .order_by(Account.id.asc())
        .all()
    )
    return accounts


def get_account_by_id(db: Session, account_id: int, user_id: int = DEFAULT_USER_ID) -> Account:
    """Retrieve a specific account belonging to the user or raise 404."""
    account = (
        db.query(Account)
        .filter(Account.id == account_id, Account.user_id == user_id)
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with ID {account_id} not found",
        )
    return account


def get_user_transactions(
    db: Session,
    user_id: int = DEFAULT_USER_ID,
    account_id: Optional[int] = None,
) -> List[Transaction]:
    """
    Retrieve transaction history for the user from CQRS transaction projections.
    If account_id is specified, filter by account after verifying ownership.
    """
    if account_id is not None:
        get_account_by_id(db, account_id, user_id)
        transactions = (
            db.query(Transaction)
            .filter(Transaction.account_id == account_id)
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
            .all()
        )
    else:
        user_account_ids = [
            acc.id for acc in db.query(Account.id).filter(Account.user_id == user_id).all()
        ]
        transactions = (
            db.query(Transaction)
            .filter(Transaction.account_id.in_(user_account_ids))
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
            .all()
        )

    account_map = {acc.id: acc.account_name for acc in get_user_accounts(db, user_id)}
    for tx in transactions:
        setattr(tx, "account_name", account_map.get(tx.account_id, "Unknown Account"))

    return transactions
