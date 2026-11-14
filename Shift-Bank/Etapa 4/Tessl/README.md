# Shift Bank — Stage 3 (Tessl Specification-Driven Development)

Shift Bank Stage 3 is an enterprise-grade banking web application developed for an authenticated mock user (**Alex Morgan**) following Tessl's **Specification-Driven Development (SDD)** methodology.

Stage 3 extends the brownfield Stage 2 foundation with advanced cybersecurity, transactional auditing, containerized infrastructure, and load performance testing.

---

## Capabilities Overview

### Stage 1 & 2 Inherited Features
1. **Core Accounts & Balances:**
   - Pre-seeded accounts: **Primary Checking** (CHK-1001, $2,500.00) and **Standard Savings** (SAV-2001, $10,000.00).
   - Real-time aggregate balance calculation ($12,500.00) and interactive account filtering.
2. **Internal Account Transfers:**
   - Atomic fund transfers between own accounts with strict balance and decimal validations.
3. **Transaction History & Ledger:**
   - Synchronized double-entry transaction records with reference codes, timestamps, and balance-after tracking.
4. **Mock Multi-Factor Authentication (MFA):**
   - Threshold-triggered PIN verification for transfers exceeding **,000.00**; account lockout after 3 consecutive failed attempts (HTTP 423 Locked).
5. **ACH Interbank Transfers:**
   - Beneficiary lifecycle management (saved and ad-hoc), routing number validations, simulated asynchronous settlement, and automated refund on settlement failure.
6. **Recurring Payments Scheduling:**
   - Automated scheduling (daily, weekly, monthly) powered by a background scheduler; support for pause, resume, and cancellation workflows.
7. **Dynamic Transfer Limits:**
   - Per-transaction and daily aggregate limit enforcement with real-time remaining allowance calculation.

### Stage 3 Advanced Capabilities
1. **End-to-End Field-Level & At-Rest Encryption:**
   - **Client-Side Hybrid Encryption:** Frontend hybrid envelope encryption using RSA-OAEP (SHA-256) for ephemeral AES-256 session keys and AES-256-GCM for sensitive fields (routing numbers, account numbers).
   - **Key Lifecycle:** Dynamic RSA-2048 keypair retrieval via GET /api/crypto/public-key with key ID indexing and expiration validation.
   - **Storage Encryption:** Server-side AES-256-GCM encryption at rest (enc:v1:<iv>:<ciphertext>:<tag>).
   - **Idempotent Migration:** Automated, fail-fast, atomic startup migration routine (un_migration) that verifies 100% of sensitive records before committing.
2. **Cryptographic Append-Only Audit Ledger:**
   - Chained HMAC-SHA256 audit ledger from a deterministic genesis block to the chain head.
   - **Fail-Closed Guarantee:** Any failure to persist an audit entry rolls back the primary banking transaction.
   - **Database Triggers:** SQLite database-level triggers blocking UPDATE and DELETE operations on the udit_log table.
   - **Ledger Verification:** Protected endpoint GET /api/audit/verify requiring X-Admin-Key authorization to verify chain integrity.
3. **Containerized Production Deployment & Security Hardening:**
   - Multi-container Docker Compose deployment (shiftbank-backend and shiftbank-frontend).
   - **Non-Root Runtime:** Unprivileged execution using ppuser (UID 1000) for FastAPI and 
ginx for Nginx.
   - **TLS Reverse Proxy:** Nginx terminating TLSv1.2/TLSv1.3 on port 8443 (mapped to host 443) with automatic HTTP-to-HTTPS redirect on port 8080 (mapped to host 80).
   - **Strict Secrets Management:** Mandatory ENCRYPTION_KEY, AUDIT_SECRET_KEY, and ADMIN_SECRET_KEY with Compose validation guards (${VAR:?error}) and FastAPI lifespan fail-fast assertions.
   - **Volume Persistence:** Persistent SQLite storage mounted at shiftbank_data:/app/data.
4. **Automated Load Testing & Performance Benchmarking:**
   - Headless Locust workload simulating 100 concurrent banking users over an isolated test database (	est_load.db).
   - SLA compliance verified: 95th percentile latency of **12.8 ms** (SLA < 200 ms) and **0.0% failure rate** (SLA < 1.0%).

---

## Specification-Driven Development (SDD) Structure

All capabilities are governed by specifications in the specs/ directory and verified by linked automated tests:

| Specification | Focus Area | Verified By |
|---|---|---|
| [specs/accounts.spec.md](specs/accounts.spec.md) | Account balances & summaries | ackend/tests/test_accounts.py, rontend/src/__tests__/AccountSummary.test.tsx |
| [specs/transfers.spec.md](specs/transfers.spec.md) | Internal transfers & thresholds | ackend/tests/test_transfers.py, rontend/src/__tests__/TransferModal.test.tsx |
| [specs/transactions.spec.md](specs/transactions.spec.md) | Transaction history ledger | ackend/tests/test_transactions.py, rontend/src/__tests__/TransactionHistory.test.tsx |
| [specs/mfa.spec.md](specs/mfa.spec.md) | MFA PIN challenge & lockout | ackend/tests/test_mfa.py, rontend/src/__tests__/MfaModal.test.tsx |
| [specs/ach_transfers.spec.md](specs/ach_transfers.spec.md) | ACH transfers & beneficiaries | ackend/tests/test_ach_transfers.py, rontend/src/__tests__/TransferModal.test.tsx |
| [specs/recurring_payments.spec.md](specs/recurring_payments.spec.md) | Recurring payments & scheduler | ackend/tests/test_recurring_payments.py, rontend/src/__tests__/RecurringPayments.test.tsx |
| [specs/transfer_limits.spec.md](specs/transfer_limits.spec.md) | Dynamic transfer limits | ackend/tests/test_transfer_limits.py, rontend/src/__tests__/TransferLimits.test.tsx |
| [specs/encryption.spec.md](specs/encryption.spec.md) | Field-level & at-rest encryption | ackend/tests/test_encryption.py, rontend/src/__tests__/crypto.test.ts |
| [specs/audit_log.spec.md](specs/audit_log.spec.md) | Cryptographic audit ledger | ackend/tests/test_audit_log.py |
| [specs/load_testing.spec.md](specs/load_testing.spec.md) | Load testing & SLA benchmarks | ackend/tests/test_load_performance.py, ackend/tests/load/locustfile.py |
| [specs/deployment.spec.md](specs/deployment.spec.md) | Docker Compose & HTTPS deployment | ackend/tests/test_deployment_config.py, ackend/tests/test_live_deployment_smoke.py |

---

## How to Run the Application

### Option A: Local Development Mode

#### 1. Backend (FastAPI / SQLite)
`ash
# Set required development secrets
export ENCRYPTION_KEY="01234567890123456789012345678901"
export AUDIT_SECRET_KEY="local_dev_audit_secret_key_32b!"
export ADMIN_SECRET_KEY="local_dev_admin_secret_key_2026"

# Install dependencies and run backend
pip install -r backend/requirements.txt
python backend/run.py
`
*API documentation (Swagger UI) is available at http://localhost:8000/docs.*

#### 2. Frontend (React / Vite)
`ash
cd frontend
npm install
npm run dev
`
*Frontend runs at http://localhost:5173.*

### Option B: Production Containerized Mode (Docker Compose)

`ash
# 1. Configure environment variables (or copy .env.example to .env and set strong secrets)
export ENCRYPTION_KEY="your-32-byte-hex-or-raw-encryption-key"
export AUDIT_SECRET_KEY="your-strong-hmac-audit-signing-key"
export ADMIN_SECRET_KEY="your-admin-endpoint-secret-key"

# 2. Generate local TLS certificates (if not already present)
python nginx/generate_certs.py

# 3. Build and launch containers
docker compose up -d --build
`
*Application is served over HTTPS at https://localhost with HTTP traffic automatically redirected from http://localhost.*

---

## Running the Automated Test Suites

### Backend Unit & Integration Tests (Pytest)
`ash
python -m pytest backend/tests -v
`
*86 tests covering accounts, transfers, ACH, recurring payments, MFA, limits, encryption, audit chaining, deployment config, and load SLA verification.*

### Frontend Component & Crypto Tests (Vitest)
`ash
cd frontend
npx vitest run
`
*39 tests covering AccountSummary, TransferModal, TransactionHistory, MfaModal, RecurringPayments, TransferLimits, and RSA-OAEP/AES-GCM client-side crypto utilities.*

### Production Build Verification
`ash
cd frontend
npm run build
`
*Compiles TypeScript and bundles production assets via Vite with zero type errors.*

### Load Performance Benchmark
`ash
python backend/tests/load/run_load_test.py
`
*Executes the headless Locust benchmark against an isolated database and validates SLA metrics.*

### Live HTTPS Container Smoke Tests
`ash
# Requires running containers (e.g. docker compose up -d)
python backend/tests/test_live_deployment_smoke.py
`
*Validates full end-to-end HTTPS communication, reverse proxy routing, client encryption, MFA challenge, and volume persistence across container restarts.*

---

## Deep Technical Documentation

For complete architectural details, cryptographic envelope specifications, audit block structures, and operational constraints, see [docs/STAGE3_TECHNICAL.md](docs/STAGE3_TECHNICAL.md).
