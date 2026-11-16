# Implementation Plan: Shift Bank Stage 3 — Security Hardening, Audit Integrity, Load Testing, and Containerized Deployment

**Branch**: `003-shift-bank-stage3` | **Date**: 2026-11-15 | **Spec**: [specs/003-shift-bank-stage3/spec.md](spec.md)

**Input**: Approved Stage 3 feature specification from `/specs/003-shift-bank-stage3/spec.md`

## Summary

Evolve the brownfield Shift Bank Stage 2 application with Stage 3 (Option A: Enterprise Hardening and Operational Readiness) capabilities:
1. **Application-Layer Encryption (E3-ENC-01)**: Client-originated banking payloads (beneficiary details, account numbers, amounts, MFA PINs) encrypted in browser using native Web Crypto (`SubtleCrypto`) hybrid envelope encryption (RSA-OAEP + AES-256-GCM); decrypted in memory by the trusted FastAPI backend.
2. **Encrypted Persistence & Exact Arithmetic (E3-ENC-01, FR-009..FR-013)**: Authenticated encryption at rest (AES-256-GCM) for sensitive banking identifiers and financial amounts in SQLite; amounts decrypted into memory as exact Python `Decimal` values to preserve dynamic limits, ledger consistency, and precision invariants. Includes safe, atomic, idempotent legacy plaintext migration.
3. **Tamper-Evident Chained Audit Ledger (E3-AUD-01, FR-014..FR-023)**: Monotonic append-only SQLite audit table linked via keyed HMAC-SHA256 digests; contiguous gap-free sequence calculation under `BEGIN IMMEDIATE`; atomic commit with financial mutations (fail-closed rollback); SQLite abort triggers blocking updates/deletes; administrative verification interface protected by credentials and capable of detecting tail truncation against an external trusted checkpoint.
4. **Reproducible Locust Load Testing (E3-LOAD-01, FR-024..FR-029)**: Automated Locust benchmark exercising the real encrypted HTTP interface for 66 seconds (6s ramp-up to 30 users at 5/s, followed by 60s sustained steady-state hold; target weights 60% balance, 30% history, 10% transfers); measures actual distribution; separates expected banking rejections from unexpected errors (< 1.0% failure target); uses isolated disposable synthetic database.
5. **Containerized HTTPS Deployment (E3-DEP-01, FR-030..FR-035)**: Multi-container Docker Compose setup with Nginx reverse proxy terminating local TLS, redirecting HTTP (port 8080) to HTTPS (port 8443), serving production-built React frontend assets, and routing API calls to containerized FastAPI backend with persistent SQLite volume storage and exactly one scheduler instance.

---

## Technical Context

**Language/Version**: Python 3.13 (Backend), TypeScript 5.5+ / React 18+ (Frontend)

**Primary Dependencies**:
- Backend: `fastapi`, `uvicorn`, `pydantic`, `cryptography` (for RSA/AES-GCM/HMAC), `locust` (for load testing).
- Frontend: `react`, `react-dom`, `vite` (dev/build), standard browser Web Crypto API (`window.crypto.subtle`). No external client crypto libraries needed.
- Infrastructure: Docker, Docker Compose, Nginx (Alpine-based official image).

**Storage**: SQLite (`sqlite3`) with persistent volume mounting for container deployment. Single-process execution mandate (`uvicorn --workers 1`) with write operations executed under `BEGIN IMMEDIATE` transaction locks.

**Testing**: `pytest` and `httpx` (Backend); `vitest` and `@testing-library/react` (Frontend); `locust` (Load testing); Python/PowerShell smoke test script (Deployment verification). Tests execute against isolated temporary test databases (`TEST_DB_PATH`) to protect runtime data.

**Target Platform**: Local development and containerized multi-platform Linux/Windows environment (Docker Compose).

**Project Type**: Web application / API microservice (Brownfield evolution).

**Performance Goals**: Read operations p95 < 200 ms; transfer operations p95 < 500 ms; unexpected error rate < 1.0% under 30 concurrent users.

**Constraints**:
- Exact Colombian Peso (`COP`) currency representation using Python `Decimal` (no floating-point rounding drift).
- Strict trust boundary: Application-layer encryption for client-originated sensitive data; HTTPS transport security for server responses and transit. No symmetric server secrets exposed to React client.
- Fail-closed atomicity: Financial mutation and chained audit record must commit together; audit failure mandates transaction rollback.
- Tail truncation detection explicitly requires comparison against an external trusted checkpoint.
- Threat model excludes hardware WORM claims or administrator with full root/storage/key access.

**Scale/Scope**: Single authenticated mock user (`user_mock_001`), Checking and Savings accounts, dynamic limits, recurring schedules, and ACH transfers.

---

## Constitution Check

*GATE: Evaluated and passed against Shift Bank Constitution v1.2.0.*

- **Specification Authority (Principle I)**: PASS. All planned capabilities map directly to approved requirements (FR-001 through FR-035) and clarification decisions E3-ENC-01, E3-AUD-01, E3-LOAD-01, and E3-DEP-01. Live clearing networks, multi-tenant auth, public cloud CI/CD, and loan/card products remain strictly out of scope.
- **Specification-First Changes (Principle II)**: PASS. The Stage 3 feature specification (`spec.md`) and quality checklist were formally approved before generating technical planning artifacts.
- **Proportional Implementation (Principle III)**: PASS. Architecture remains proportional to the existing FastAPI/React/SQLite stack. Employs standard Python `cryptography`, browser Web Crypto, and standard Nginx reverse proxy without heavy distributed queues or external database engines.
- **Requirement-Driven Validation (Principle IV)**: PASS. Every functional requirement and acceptance scenario maps to verifiable automated checks (pytest, vitest, locust, smoke tests).
- **Strict Scope Compliance (Principle V)**: PASS. Preserves all inherited Stage 1 and Stage 2 banking rules, COP currency, and mock user isolation.
- **Workflow & Tool Neutrality**: PASS. Uses standard open-source tools (pytest, vitest, locust, docker-compose) without proprietary platform lock-in.

---

## Project Structure

### Documentation (this feature)

```text
specs/003-shift-bank-stage3/
├── spec.md              # Approved Stage 3 feature specification (35 FRs, 38 scenarios)
├── plan.md              # This file (Technical Implementation Plan)
├── research.md          # Technical research log & architectural tradeoffs
├── data-model.md        # Extended SQLite schema, entity models, audit ledger & migration
├── quickstart.md        # Runnable verification and testing guide
├── checklists/
│   └── requirements.md  # Requirements quality validation checklist (16/16 verified)
└── contracts/
    └── api.md           # REST API endpoint contract definitions & cryptographic schemas
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── api.py                   # FastAPI REST endpoints (+ /crypto, /audit, /health)
│   ├── crypto.py                # Cryptographic service: RSA unwrap, AES-GCM at rest, HMAC chaining
│   ├── database.py              # SQLite connection, audit triggers, legacy plaintext migration
│   ├── main.py                  # FastAPI app bootstrapper with background lifespan worker
│   ├── models.py                # Pydantic schemas (+ CryptographicEnvelope, AuditRecord, HealthResponse)
│   ├── scheduler.py             # Background worker: recurring schedules, ACH settlement, audit logging
│   └── services.py              # Domain logic: encrypted persistence, exact Decimal arithmetic, audit atomicity
├── requirements.txt             # Added: cryptography, locust
└── tests/
    ├── conftest.py              # Test database fixtures, cryptographic test keys, TEST_DB_PATH
    ├── locustfile.py            # Locust load testing benchmark script
    ├── test_api.py              # Inherited Stage 1 tests (preserved)
    ├── test_stage2_regression.py # Inherited Stage 2 tests (preserved)
    ├── test_crypto.py           # Unit tests for envelope encryption & at-rest decryption
    ├── test_migration.py        # Tests for safe, idempotent legacy plaintext migration & rollback
    ├── test_audit.py            # Tests for audit chaining, atomicity, fail-closed rollback, triggers & verify
    └── test_smoke.py            # Deployment smoke verification suite

frontend/
├── src/
│   ├── App.css                  # Vanilla CSS layout and tab/modal styling
│   ├── App.tsx                  # Main React layout with section tabs & state orchestration
│   ├── crypto.ts                # Web Crypto API client wrapper (RSA key fetch, AES-GCM envelope)
│   ├── services.ts              # API client functions with transparent payload encryption
│   └── types.ts                 # TypeScript interfaces (+ CryptoEnvelope, AuditVerification)
├── package.json                 # Frontend dependencies and test scripts
└── vite.config.ts               # Vite build configuration

deployment/
├── certs/
│   ├── server.crt               # Local development SSL certificate
│   └── server.key               # Local development SSL private key
├── nginx.conf                   # Nginx reverse proxy configuration (TLS termination, HTTP redirect, proxy)
├── Dockerfile.backend           # Containerfile for FastAPI backend (Python 3.13-slim, non-root)
├── Dockerfile.frontend          # Multi-stage or static Nginx containerfile for React build
├── docker-compose.yml           # Multi-container orchestration (nginx, backend, persistent volume)
└── .env.example                 # Example deployment environment configuration
```

---

## Technical Architecture & Design Decisions

### 1. Application-Layer Client-to-Server Encryption (`crypto.py`, `crypto.ts`)
- **Backend Keypair**: An asymmetric RSA keypair (2048-bit RSA-OAEP with SHA-256) is configured via `BANK_PRIVATE_KEY_PATH`. On startup, `api.py` exposes `GET /api/crypto/public-key` returning the RSA public key in PEM format.
- **Client Encryption Envelope**:
  - `crypto.ts` exports `encryptPayload(data: object): Promise<CryptographicEnvelope>`.
  - Generates an ephemeral 256-bit AES-GCM key (`crypto.subtle.generateKey`).
  - Encrypts JSON serialized payload with AES-GCM using a random 12-byte IV.
  - Encrypts the raw AES key using the cached backend RSA public key (`RSA-OAEP`).
  - Returns:
    ```typescript
    interface CryptographicEnvelope {
      encrypted_key: string; // Base64 RSA-wrapped AES key
      iv: string;            // Base64 12-byte IV
      ciphertext: string;    // Base64 ciphertext
      tag: string;           // Base64 16-byte authentication tag
    }
    ```
- **Backend Decryption**:
  - `crypto.py` unwraps `encrypted_key` using server RSA private key.
  - Decrypts and authenticates `ciphertext` using AES-256-GCM.
  - Deserializes into target Pydantic model (`TransferCreate`, `AchTransferCreate`, `BeneficiaryCreate`, `MFACodeConfirm`).
  - Any decryption failure (corrupted data, tag mismatch) raises `HTTPException(400, "Invalid cryptographic envelope")`. Plaintext fallback is strictly prohibited.
- **Response Protection**: Server responses carry sensitive data over mandatory HTTPS TLS transport.

### 2. Encrypted Storage at Rest & Exact Decimal Arithmetic (`services.py`, `database.py`)
- **At-Rest Field Encryption**:
  - Uses `BANK_STORAGE_KEY` (256-bit symmetric key).
  - Encrypts values into prefixed string format: `enc:v1:<iv_b64>:<ciphertext_tag_b64>`.
  - Encrypted fields:
    - `accounts`: `balance`.
    - `transfers`: `amount`, `recipient_name`, `bank_name`, `routing_number`, `account_number`.
    - `beneficiaries`: `name`, `bank_name`, `routing_number`, `account_number`.
    - `limits`: `per_transfer_limit`, `daily_limit`.
    - `recurring_schedules`: `amount`, `recipient_name`, `bank_name`, `routing_number`, `account_number`.
- **Exact Decimal Arithmetic**:
  - Encrypted amounts are stored as exact decimal strings (e.g. `"1500000.00"`).
  - On retrieval, `services.py` decrypts the string and instantiates Python `Decimal(value)`.
  - Dynamic limit checks (`get_daily_consumption`) decrypt amounts for eligible transfers and aggregate using `Decimal += Decimal(...)`.
  - Zero floating-point drift or precision loss.

### 3. Safe, Idempotent Legacy Plaintext Migration (`database.py`)
- Executed inside `init_db()` during application boot:
  1. Inspects all sensitive fields across all records in `accounts`, `limits`, `beneficiaries`, `transfers`, and `recurring_schedules`.
  2. For each field:
     - If `NULL`: leaves as `NULL`.
     - If valid `enc:v1:...`: validates structure; aborts and rolls back if envelope is corrupted.
     - If unencrypted plaintext: encrypts using `BANK_STORAGE_KEY` and updates row.
  3. Executes inside `BEGIN IMMEDIATE TRANSACTION`.
  4. If any exception occurs: executes `ROLLBACK`, leaving original database state intact, and raises error.
  5. Idempotent: rows already starting with valid `enc:v1:` are untouched on subsequent runs.
  6. Strictly isolated from historical Stage 1/Stage 2 reference databases.

### 4. Tamper-Evident Chained Audit Ledger (`audit_logs`)
- **Table Schema**:
  ```sql
  CREATE TABLE IF NOT EXISTS audit_logs (
      id INTEGER PRIMARY KEY,                  -- Strictly contiguous sequence: 1, 2, 3...
      timestamp TEXT NOT NULL,
      event_type TEXT NOT NULL,
      actor_id TEXT NOT NULL,
      resource_id TEXT,
      payload_digest TEXT NOT NULL,
      previous_hash TEXT NOT NULL,
      record_hmac TEXT NOT NULL
  );
  ```
- **Contiguous Sequence Calculation**:
  - Explicitly allocated under `BEGIN IMMEDIATE;` lock:
    ```sql
    SELECT COALESCE(MAX(id), 0) + 1,
           COALESCE((SELECT record_hmac FROM audit_logs WHERE id = (SELECT MAX(id) FROM audit_logs)),
                    '0000000000000000000000000000000000000000000000000000000000000000')
    FROM audit_logs;
    ```
  - Eliminates sequence gaps caused by SQLite AUTOINCREMENT on rollbacks.
- **Database Abort Triggers**:
  ```sql
  CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_update BEFORE UPDATE ON audit_logs
  BEGIN SELECT RAISE(ABORT, 'Audit log is append-only: updates prohibited'); END;
  CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_delete BEFORE DELETE ON audit_logs
  BEGIN SELECT RAISE(ABORT, 'Audit log is append-only: deletions prohibited'); END;
  ```
- **Chaining Formula**:
  $$\text{record\_hmac}_i = \text{HMAC-SHA256}(K_{\text{audit}},\, \text{previous\_hash}_i \parallel \text{id}_i \parallel \text{timestamp}_i \parallel \text{event\_type}_i \parallel \text{actor\_id}_i \parallel \text{resource\_id}_i \parallel \text{payload\_digest}_i)$$
- **Atomicity & Fail-Closed**:
  - `services.py` executes financial operations and `INSERT INTO audit_logs` within the same SQLite connection transaction.
  - If audit write fails: `conn.rollback()` rolls back balance debits and transfer creation.
  - Rejection events (e.g. limit exceeded, bad MFA) are logged in a separate atomic transaction; if logging fails, the operation rejects safely.
- **Verification Endpoint (`GET /api/audit/verify`)**:
  - Protected by `X-Audit-Admin-Key` header matching `AUDIT_ADMIN_KEY`. Missing/invalid header returns HTTP 401/403.
  - Traverses entire ledger, recomputes digests and HMACs, validates sequence continuity.
  - Accepts optional query parameters `expected_head_hash` and `expected_count` to detect tail truncation against an external trusted checkpoint.

### 5. Reproducible Locust Load Testing (`backend/tests/locustfile.py`)
- Target: Live FastAPI backend over HTTP/HTTPS.
- Timing Profile: 30 concurrent users, spawn rate 5 users/s (6s ramp-up), sustained hold for 60s post ramp-up (total test duration: 66s).
- Configured task weights:
  - `@task(6)`: `get_accounts` (60%)
  - `@task(3)`: `get_history` (30%)
  - `@task(1)`: `create_transfer` (10%, uses client-side encryption simulation)
- Metrics & Isolation:
  - Uses dedicated disposable database (`test_load_bank.db`) pre-seeded with COP 100,000,000.00 balances and COP 50,000,000.00 limits.
  - Classifies responses into Success (200/201), Expected Banking Rejection (400), and Unexpected Failure (5xx, network error).
  - Target: Read p95 < 200 ms, transfer p95 < 500 ms, unexpected error rate < 1.0% during the 60-second steady-state window.
  - Persists first valid report to `locust/reports/` without overwriting.

### 6. Containerized Deployment (`deployment/`)
- Multi-container Docker Compose architecture:
  - `nginx`: Reverse proxy on host ports 8080 (HTTP $\to$ HTTPS redirect) and 8443 (HTTPS termination). Serves static React assets, proxies `/api/` to backend.
  - `backend`: Containerized FastAPI application running Uvicorn on port 8000, non-root user `bankuser`. Mounts persistent SQLite volume `shift_bank_data:/app/data`.
  - Single active scheduler instance running within backend lifespan.
  - Health checks on both containers (`/api/health`).
  - Automated smoke test (`test_smoke.py`) validates redirection, API health, account operations, encrypted transactions, MFA step-up, audit verification, and restart persistence.

---

## Inherited Compatibility Matrix

| Capability / Entity | Stage 2 Contract (`specs/002-.../contracts/api.md`) | Stage 3 Planning Artifacts | Status |
|---|---|---|---|
| Transfer Statuses | `COMPLETED`, `PENDING`, `PENDING_MFA`, `SETTLED`, `FAILED`, `EXPIRED` | Identical statuses preserved; `refunded_at` timestamp records ACH refunds | **100% Match** |
| Recurring Schedule Statuses | `ACTIVE`, `PAUSED`, `CANCELLED`, `PENDING_MFA`, `EXPIRED` | Identical statuses preserved | **100% Match** |
| Dynamic Limits | Per-transfer & daily limits in COP; evaluated before MFA | Evaluated in memory via exact `Decimal` arithmetic; migrated to encrypted at rest | **100% Match** |
| Simulated MFA | Threshold $\ge \text{COP } 1,000,000.00$, code `123456`, 300s window | Transmitted in encrypted envelope; validated in memory; never logged | **100% Match** |
| Beneficiary Fields | `id`, `user_id`, `name`, `bank_name`, `routing_number`, `account_number`, `created_at` | Identical columns; sensitive fields (`name`, `bank_name`, `routing_number`, `account_number`) encrypted at rest | **100% Match** |
| Transfers Schema | 15 columns including `settled_at`, `failed_at`, `refunded_at` | Identical columns preserved; sensitive fields encrypted at rest | **100% Match** |
| Recurring Schema | 16 columns including `next_due_date`, `mfa_expires_at` | Identical columns preserved; sensitive fields encrypted at rest | **100% Match** |
| API Endpoints | 16 REST endpoints across accounts, transfers, limits, beneficiaries, schedules | All 16 endpoints preserved; sensitive mutations wrap request bodies in `CryptographicEnvelope` | **100% Match** |
