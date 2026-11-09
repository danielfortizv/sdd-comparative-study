# Shift Bank - Stage 1 (Tessl Specification-Driven Development)

Shift Bank Stage 1 is an online banking web application built for an authenticated mock user (**Alex Morgan**) following Tessl's **Specification-Driven Development (SDD)** methodology.

## Features Implemented

1. **Bank Accounts & Balances:**
   - Display pre-seeded accounts: **Primary Checking** (`CHK-1001`, `$2,500.00`) and **Standard Savings** (`SAV-2001`, `$10,000.00`).
   - Summary card calculating aggregate net balance (`$12,500.00`).
   - Interactive account filtering to view movements per account.

2. **Internal Account Transfers:**
   - Transfer money between own accounts with strict validation (positive amount, up to 2 decimal places, sufficient balance check, source ≠ destination).
   - Atomic debit/credit execution and synchronized transaction records.
   - Real-time balance and transaction history synchronization.

3. **Transaction History & Movements:**
   - Complete ledger of account movements with credit/debit indicators (`+` / `-`), transaction descriptions, reference codes, timestamps, and balance-after amounts.
   - Filter tabs: **All Accounts**, **Primary Checking**, and **Standard Savings**.

4. **Mock Multi-Factor Authentication (MFA):**
   - Threshold-triggered security check: transfers strictly exceeding **$1,000.00** require Security PIN authorization; transfers $\le$ $1,000.00 execute immediately.
   - Mock Security PIN: `1234`.
   - Security lockout: locks account operations after 3 consecutive failed PIN attempts (HTTP 423 Locked).

---

## Specification-Driven Development Structure

Specifications are maintained in the `specs/` directory and verified by linked automated tests:

- [`specs/accounts.spec.md`](specs/accounts.spec.md) $\rightarrow$ Verified by `backend/tests/test_accounts.py` and `frontend/src/__tests__/AccountSummary.test.tsx`
- [`specs/transfers.spec.md`](specs/transfers.spec.md) $\rightarrow$ Verified by `backend/tests/test_transfers.py` and `frontend/src/__tests__/TransferModal.test.tsx`
- [`specs/transactions.spec.md`](specs/transactions.spec.md) $\rightarrow$ Verified by `backend/tests/test_transactions.py` and `frontend/src/__tests__/TransactionHistory.test.tsx`
- [`specs/mfa.spec.md`](specs/mfa.spec.md) $\rightarrow$ Verified by `backend/tests/test_mfa.py` and `frontend/src/__tests__/MfaModal.test.tsx`

---

## How to Run the Application

### 1. Backend (Python / FastAPI)

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run backend server (runs at http://127.0.0.1:8000)
python backend/run.py
```

API documentation (Swagger UI) is available at: `http://127.0.0.1:8000/docs`

### 2. Frontend (React / TypeScript / Vite)

```bash
cd frontend

# Install dependencies (if not already installed)
npm install

# Start Vite dev server (runs at http://localhost:5173)
npm run dev
```

---

## Running the Automated Test Suites

### Backend Tests (Pytest)
```bash
python -m pytest backend/tests -v
```
*19 tests covering account endpoints, transfer validations, atomicity, transaction history, and MFA lockout.*

### Frontend Tests (Vitest & Testing Library)
```bash
cd frontend
npm run test
```
*21 tests covering AccountSummary, TransferModal, TransactionHistory, and MfaModal components.*
