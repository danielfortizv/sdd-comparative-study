# Technical Research & Architectural Tradeoffs: Shift Bank Stage 3

**Feature**: Shift Bank Stage 3 (Security Hardening, Audit Integrity, Load Testing, and Deployment)  
**Spec Reference**: [specs/003-shift-bank-stage3/spec.md](spec.md)  
**Date**: 2026-11-15  

---

## 1. Executive Summary & Architectural Decisions

This document investigates the technical alternatives and establishes the design decisions for implementing the four Stage 3 capabilities within the brownfield FastAPI / React / SQLite application:
1. **Application-Layer Encryption (E3-ENC-01)**: Hybrid envelope encryption (RSA-OAEP + AES-256-GCM) between browser and backend.
2. **Encrypted Persistence at Rest & Exact Arithmetic (E3-ENC-01)**: AES-256-GCM authenticated encryption for sensitive identifiers and financial amounts at rest, with Python `Decimal` in-memory arithmetic.
3. **Safe, Idempotent Legacy Migration (FR-013)**: Atomic SQLite table migration with complete multi-field validation, converting Stage 2 plaintext data to encrypted storage on startup.
4. **Tamper-Evident Transaction Audit Logs (E3-AUD-01)**: HMAC-SHA256 chained audit ledger with strictly contiguous sequence numbers, SQLite abort triggers, fail-closed atomicity, external checkpoint validation, and administrative authorization.
5. **Reproducible Locust Load Testing (E3-LOAD-01)**: Standard Locust suite targeting the real encrypted HTTP interface for 66s (6s ramp + 60s steady-state) with synthetic data isolation and error classification.
6. **Containerized HTTPS Deployment (E3-DEP-01)**: Multi-container Docker Compose setup with Nginx reverse proxy terminating TLS, serving production React assets, and persistent SQLite volume storage.

---

## 2. Research Topic 1: Application-Layer Client-to-Server Encryption & Key Management

### Context & Constraint
- Requirement: Sensitive client-originated banking payloads (beneficiary names, account numbers, routing numbers, amounts, MFA PINs) must be encrypted in the browser before network transmission and decrypted by the trusted backend in memory (E3-ENC-01, FR-001..FR-008).
- Constraint: A long-lived symmetric server secret MUST NOT be exposed to the React client (Milestone 2 Human Review finding 1).
- Constraint: Server responses carrying sensitive information rely on mandatory transport-level HTTPS protection; no unapproved application-layer response payload re-encryption is imposed (Milestone 2 Human Review finding 6).

### Evaluated Alternatives
1. **Option A: Pre-shared Symmetric Key**: Embed or configure a symmetric key (AES-GCM) in the React bundle.
   - *Pros*: Simple symmetric encryption.
   - *Cons*: Severe security vulnerability. Any client or inspector can extract the key and decrypt all payloads. Fails review requirement.
2. **Option B: Asymmetric Public-Key Hybrid Envelope Encryption (Selected)**:
   - The backend holds an RSA private key (2048-bit, PKCS#1 v2.1 / OAEP with SHA-256) loaded from an external file/environment variable (`BANK_PRIVATE_KEY_PATH`).
   - The backend publishes its RSA public key in PEM or JWK format via an unauthenticated endpoint: `GET /api/crypto/public-key`.
   - The React client uses the standard browser Web Crypto API (`window.crypto.subtle`):
     1. Generates an ephemeral, cryptographically random 256-bit symmetric key (`crypto.getRandomValues`) for AES-GCM.
     2. Encrypts the sensitive JSON payload using AES-256-GCM with a fresh 12-byte initialization vector (IV).
     3. Encrypts (wraps) the ephemeral AES key using the backend's RSA-OAEP public key.
     4. Transmits an envelope structure: `{ "encrypted_key": "...", "iv": "...", "ciphertext": "...", "tag": "..." }`.
   - The backend unwraps the ephemeral AES key with its private key and decrypts the payload in memory.
   - *Pros*: Standard hybrid cryptosystem; zero server symmetric secrets in client; works seamlessly with native browser Web Crypto API; no third-party JavaScript crypto dependencies required.
   - *Cons*: Requires asymmetric key operations on client and server; performance impact is unverified until empirical testing in Stage 3.

### Decision
Implement **Option B (Asymmetric Hybrid Envelope Encryption)**. Use `cryptography` in Python for backend decryption and `SubtleCrypto` in TypeScript for client encryption. Server responses rely on mandatory HTTPS TLS transport encryption.

---

## 3. Research Topic 2: Encrypted Persistence at Rest & Exact Arithmetic

### Context & Constraint
- Requirement: Persisted sensitive identifiers (beneficiary accounts, routing numbers, recipient names, bank names) and financial amounts (`transfers.amount`, `accounts.balance`, `recurring_schedules.amount`, dynamic limits) must be encrypted using authenticated encryption at rest (FR-009, FR-010, SC-002).
- Constraint: Financial amounts must maintain exact two-decimal arithmetic and ledger consistency without rounding drift or IEEE 754 precision loss.
- Baseline Analysis: In `backend/src/services.py`, the existing codebase already enforces a precision invariant prohibiting SQLite `SUM()`: all financial records are fetched and aggregated in Python using `decimal.Decimal`.

### Evaluated Alternatives
1. **Option A: SQLite Full Database Encryption (SQLCipher)**:
   - *Pros*: Transparent at-rest encryption.
   - *Cons*: Requires compiling and linking native C libraries (`pysqlcipher3`), complicating containerization and Windows local execution. Violates proportionality (Constitution Principle III).
2. **Option B: Application-Level Field-Level Authenticated Encryption (Selected)**:
   - Encrypt sensitive columns using AES-256-GCM with a server-held persistent storage key (`BANK_STORAGE_KEY`, 256-bit hex string supplied externally).
   - Columns storing encrypted data hold formatted ciphertext envelopes: `enc:v1:<iv_b64>:<ciphertext_and_tag_b64>`.
   - In `backend/src/services.py` / database helper functions:
     - Saving: Convert Python `Decimal` amount (e.g., `Decimal("1500.00")`) to exact string `"1500.00"`, encrypt with AES-GCM, and write ciphertext string to SQLite.
     - Loading: Fetch ciphertext string, decrypt with AES-GCM, and parse into Python `Decimal(decrypted_text)`.
   - *Pros*: Standard Python library (`cryptography`); no external C binaries; exact `Decimal` precision preserved; protects against raw database file inspection.
   - *Cons*: Requires decrypting amounts in memory when computing dynamic daily consumption totals; computational overhead will be empirically measured during Stage 3 load testing.

### Decision
Implement **Option B (Field-Level Authenticated Encryption with In-Memory `Decimal` Aggregation)**.

---

## 4. Research Topic 3: Safe, Idempotent Legacy Plaintext Migration

### Context & Constraint
- Requirement: Safely convert pre-existing Stage 2 plaintext banking records (account balances, transfers, beneficiaries, recurring schedules, and dynamic limits) to encrypted storage during startup (FR-013, Scenarios 1.8..1.10).
- Constraint: Complete field validation across all entities; handle mixed plaintext/encrypted states, nullable fields, and corrupted ciphertext; safe rollback on failure; idempotent restart behavior; strictly preserve historical reference databases (FR-012).

### Migration Architecture & Design
1. **Multi-Field Validation & Detection**:
   - Rather than relying on a single sample row, the migration scans every relevant sensitive column in all rows across five entities:
     - `accounts`: `balance`
     - `limits`: `per_transfer_limit`, `daily_limit`
     - `beneficiaries`: `name`, `bank_name`, `routing_number`, `account_number`
     - `transfers`: `amount`, `recipient_name`, `bank_name`, `routing_number`, `account_number`
     - `recurring_schedules`: `amount`, `recipient_name`, `bank_name`, `routing_number`, `account_number`
2. **State Classification & Error Handling per Field**:
   - `NULL` / `None`: Left as `NULL` (e.g. for internal transfers lacking ACH details).
   - Existing encrypted value (`enc:v1:...`): Validates envelope structure (4 colon-separated parts, valid base64). If an envelope is malformed or corrupted, aborts migration and rolls back with an explicit error.
   - Plaintext value (lacks `enc:v1:`): Encrypted using `BANK_STORAGE_KEY` and updated.
3. **Transactional Rollback & Idempotency**:
   - Entire migration executes inside an exclusive SQLite transaction (`BEGIN IMMEDIATE;`).
   - If any encryption or update fails, `conn.rollback()` executes immediately, preserving the original database state.
   - Subsequent executions detect that all fields are already encrypted and valid, resulting in zero writes (idempotent).
   - Historical Stage 1 and Stage 2 databases remain completely isolated and untouched.

---

## 5. Research Topic 4: Tamper-Evident Chained Audit Trail & Contiguous Sequencing

### Context & Constraint
- Requirement: Tamper-evident, append-only audit trail capturing all financial and security state changes (E3-AUD-01, FR-014..FR-023).
- Constraint: Plaintext MFA PINs and keys must never appear in logs (E3-AUD-01, FR-008).
- Constraint: SQLite `AUTOINCREMENT` does not guarantee gap-free sequences upon rollback; contiguous sequencing must be guaranteed under concurrent transactions.
- Constraint: Tail truncation detection requires comparison against an external trusted checkpoint.
- Constraint: Administrative verification must be protected against unauthorized access without introducing a full multi-tenant authentication system.

### Cryptographic Chaining & Sequencing Architecture
- **Table Schema (`audit_logs`)**:
  - `id`: INTEGER PRIMARY KEY (strictly contiguous sequence $\text{seq}_i$).
  - `timestamp`: ISO-8601 UTC timestamp string.
  - `event_type`: Categorical string.
  - `actor_id`: User or system actor (`user_mock_001`, `system_scheduler`).
  - `resource_id`: Resource ID (`tr_xxx`, `lim_xxx`, `sch_xxx`).
  - `payload_digest`: SHA-256 hash of canonical JSON snapshot of non-sensitive event metadata.
  - `previous_hash`: Cryptographic digest of entry $i-1$ (genesis entry uses 64 zeros `0000...0000`).
  - `record_hmac`: Keyed HMAC computed over entry data:
    $$\text{HMAC-SHA256}\Big(K_{\text{audit}},\, \text{previous\_hash} \parallel \text{id} \parallel \text{timestamp} \parallel \text{event\_type} \parallel \text{actor\_id} \parallel \text{resource\_id} \parallel \text{payload\_digest}\Big)$$
- **Guaranteed Contiguous Sequencing**:
  - Sequence numbers are computed within the write transaction under `BEGIN IMMEDIATE;`:
    ```sql
    SELECT COALESCE(MAX(id), 0) + 1,
           COALESCE((SELECT record_hmac FROM audit_logs WHERE id = (SELECT MAX(id) FROM audit_logs)),
                    '0000000000000000000000000000000000000000000000000000000000000000')
    FROM audit_logs;
    ```
  - Because `BEGIN IMMEDIATE` serializes write operations and rolled-back transactions do not commit sequence numbers, no sequence gaps can occur ($1, 2, 3, \dots, N$).
- **Database-Level Immutability**:
  - SQLite abort triggers (`BEFORE UPDATE`, `BEFORE DELETE`) prevent application updates and deletions.
- **Fail-Closed Atomicity**:
  - Financial mutation and audit record insertion commit in the same transaction. Audit failure triggers complete financial rollback.
- **External Trusted Checkpoints (Tail Truncation)**:
  - Checkpoint tuple: `(sequence, head_hmac, timestamp)` exported periodically by an external administrative process or monitoring job to an external storage medium.
  - When `GET /api/audit/verify` receives `expected_head_hash` and `expected_count`:
    - If current max sequence < expected_count: Tail truncation detected.
    - If current max sequence == expected_count and head HMAC != expected_head_hash: Divergence/tampering detected.
    - If current max sequence > expected_count: Verifies record at expected_count matches expected_head_hash.
- **Administrative Protection**:
  - `GET /api/audit/verify` requires header `X-Audit-Admin-Key` matching `AUDIT_ADMIN_KEY`. Missing/invalid key returns HTTP 401/403.

---

## 6. Research Topic 5: Reproducible Locust Load Testing

### Context & Constraint
- Requirement: Locust benchmark running against the live backend over the real encrypted HTTP interface (E3-LOAD-01, FR-024..FR-029).
- Timing Profile: 30 concurrent users, ramp 5 users/s (6 seconds), sustained for 60 full seconds post ramp-up (total run time 66 seconds).
- Workload: Configured weights of 60% balance reads, 30% history reads, 10% transfers (distinguished from actual measured request distribution).
- Acceptance criteria: Steady-state read p95 < 200 ms, transfer p95 < 500 ms, unexpected error rate < 1.0%.

### Technical Design
1. **Timing & Measurement Window Isolation**:
   - Total test run time is configured as 66 seconds (`--run-time 66s`).
   - Steady-state period begins at $T = 6.0\text{ s}$ when 30 virtual users are fully spawned and runs until $T = 66.0\text{ s}$.
   - Metrics are recorded across both phases, with acceptance thresholds evaluated against steady-state execution.
2. **Encrypted Client Simulation in Locust (`locustfile.py`)**:
   - On startup, user fetches backend RSA public key from `/api/crypto/public-key`.
   - Transfers generate an ephemeral AES key, encrypt payload, wrap AES key with RSA public key, and post `CryptographicEnvelope`.
3. **Synthetic Data Isolation**:
   - Automated fixture seeds a dedicated database (`test_load_bank.db`) with synthetic accounts having large COP balances (COP 100,000,000.00) and high transfer limits (COP 50,000,000.00), preventing false limit or MFA triggers.
4. **Error Classification**:
   - Responses are classified into:
     - Success: HTTP 200/201.
     - Expected banking rejection: HTTP 400 with business limit/balance detail.
     - Unexpected failure: HTTP 5xx, connection timeouts, unhandled exceptions.
   - The < 1.0% failure threshold applies strictly to unexpected failures.
   - Benchmark writes output report to `locust/reports/` with initial baseline preserved without overwrite.

---

## 7. Research Topic 6: Multi-Container Local Deployment with Nginx

### Technical Design
1. **Frontend Packaging**: Compiled static React assets (`npm run build`) copied to `/usr/share/nginx/html`.
2. **Reverse Proxy Configuration (`nginx.conf`)**:
   - Port 80 (host 8080): HTTP to HTTPS redirect (`301 https://$host:8443$request_uri;`).
   - Port 443 (host 8443): SSL termination with local development certificates; serves static assets; proxies `/api/` to `http://backend:8000/api/`.
3. **Backend Packaging**:
   - `python:3.13-slim` base image, non-root user `bankuser`.
   - Persistent volume mount: `shift_bank_volume:/app/data` (`SHIFT_BANK_DB_PATH=/app/data/shift_bank.db`).
   - External secrets injected via `.env` / environment variables.
4. **Single-Instance Scheduler**: Runs within backend lifespan task in `main.py`.
5. **Health Checks & Smoke Verification**:
   - `/api/health` reports status, database connectivity, scheduler status, and key availability.
   - Script `deployment/smoke_test.py` validates redirection, health, account operations, encrypted transactions, MFA, audit verification, and restart persistence.

---

## 8. Inherited Stage 2 Contract Verification

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
