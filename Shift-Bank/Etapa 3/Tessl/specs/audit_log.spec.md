---
name: Cryptographic Audit Ledger
description: Tamper-evident, append-only SQLite audit log with SHA-256 hash chaining and HMAC-SHA256 signatures for financial transactions and security events
targets:
  - ../backend/app/models.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/routers/audit.py
---

# Cryptographic Audit Ledger

Provides an append-only, tamper-evident audit ledger capturing all financial transfers and authentication/security events. Each ledger entry is cryptographically linked to the preceding entry using SHA-256 hash chaining and signed with HMAC-SHA256.

## Data Contract

```python
class AuditLogEntry(BaseModel):
    id: int
    event_id: str                      # UUID v4 unique identifier
    timestamp: datetime                # UTC ISO-8601 timestamp
    event_type: str                    # e.g., "transfer_internal", "transfer_ach", "mfa_pin", "limit_breach"
    actor_id: Optional[int]            # Authenticated user ID or system actor (None for unauthenticated attempts)
    status: str                        # "SUCCESS" | "FAILURE"
    details: Dict[str, Any]            # Sanitized context dictionary (masked identifiers, amounts, error codes)
    previous_hash: str                 # 64-character hex SHA-256 hash of previous entry (or 64 zeros for genesis)
    current_hash: str                  # 64-character hex SHA-256 hash over entry attributes and previous_hash
    signature: str                     # 64-character hex HMAC-SHA256 signature over current_hash

class AuditVerificationResponse(BaseModel):
    valid: bool
    total_records: int
    tampered_entry_id: Optional[int] = None
    reason: Optional[str] = None       # "hash_mismatch" | "signature_mismatch" | "broken_chain"
```

## Append-Only SQLite Ledger & Chain Construction

- An `audit_logs` SQLite table stores all audit events sequentially and immutably.
  `[@test] ../backend/tests/test_audit_log.py`
- Immutability Enforcement: Direct `UPDATE` and `DELETE` operations on `audit_logs` are prevented at the database and ORM layers. Any attempt raises an internal audit integrity exception.
  `[@test] ../backend/tests/test_audit_log.py`
- Genesis Record: The initial entry in an empty ledger uses `previous_hash` equal to 64 hexadecimal zeros (`0000000000000000000000000000000000000000000000000000000000000000`).
  `[@test] ../backend/tests/test_audit_log.py`
- SHA-256 Hash Chaining: Each subsequent record computes `current_hash` as the SHA-256 digest of its canonical attributes concatenated with `previous_hash`:
  `SHA256(previous_hash + event_id + timestamp_iso + event_type + str(actor_id) + status + canonical_json_details)`.
  `[@test] ../backend/tests/test_audit_log.py`
- HMAC-SHA256 Signature: Each entry includes an HMAC-SHA256 signature calculated over `current_hash` using the server's secret signing key: `HMAC_SHA256(audit_secret_key, current_hash)`.
  `[@test] ../backend/tests/test_audit_log.py`
- Key Protection: The audit secret key is loaded exclusively from the environment variable `AUDIT_SECRET_KEY`. If the key is missing or empty at startup, the service fails fast with an initialization error. The signing key is never serialized, logged, or exposed across any API endpoint.
  `[@test] ../backend/tests/test_audit_log.py`

## Audited Event Types

- Internal Transfers: Emits audit events for every transfer attempt:
  - `transfer_internal` with `status="SUCCESS"` upon successful debit/credit execution.
  - `transfer_internal` with `status="FAILURE"` when balance, limit, or account validations fail.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_transfers.py`
- External ACH Transfers: Emits audit events for each lifecycle transition:
  - `transfer_ach_initiated` with `status="SUCCESS"` upon creation in pending status.
  - `transfer_ach_settled` with `status="SUCCESS"` upon background settlement.
  - `transfer_ach_failed` with `status="FAILURE"` upon settlement failure and balance refund.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Recurring Payments: Emits audit events for configuration and background execution:
  - `recurring_schedule_created`, `recurring_schedule_paused`, `recurring_schedule_resumed`, and `recurring_schedule_cancelled`.
  - `recurring_payment_executed` with `status="SUCCESS"` or `status="FAILURE"` upon scheduled execution.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_recurring_payments.py`
- MFA & Security Events: Emits audit events for authentication evaluations:
  - `mfa_verified` with `status="SUCCESS"` on valid PIN verification.
  - `mfa_attempt_failed` with `status="FAILURE"` and remaining attempts count on incorrect PIN.
  - `mfa_locked` with `status="FAILURE"` when 3 consecutive failed attempts lock the user.
  - `mfa_lockout_rejected` with `status="FAILURE"` when an operation is attempted while locked.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_mfa.py`
- Transfer Limit Breaches: Emits `limit_breach` with `status="FAILURE"` when an operation violates per-transaction or daily transfer limits.
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_transfer_limits.py`

## Rollback Consistency & Transaction Isolation

- Failure Preservation & Durable Audit Entries: If a financial transfer, limit validation, or security operation fails and causes the business transaction to roll back, the failure audit log entry (`status="FAILURE"`) must be durably committed in an independent, autonomous database transaction immediately after the rollback. This ensures failed operations remain auditable without being discarded by business transaction rollbacks.
  `[@test] ../backend/tests/test_audit_log.py`
- Success Atomicity: Successful business operations commit their state changes and their audit log entry atomically within the same database transaction, ensuring no completed financial operation exists without an audit record.
  `[@test] ../backend/tests/test_audit_log.py`
- Fail-Closed Audit Guarantee: If the audit service fails to compute or persist an audit entry during a financial transaction, the financial transaction must NOT commit, ensuring no un-audited state mutation can occur.
  `[@test] ../backend/tests/test_audit_log.py`

## Concurrent Writes, Multi-Process Safety & SQLite File Locking

- Multi-Process Concurrency Safety: Because the application may run across multiple server processes (e.g. multi-worker Uvicorn or separate container processes), concurrency control must not rely exclusively on in-memory Python mutexes. Chain calculation and record insertion are serialized at the database engine level using SQLite exclusive write transactions (`BEGIN IMMEDIATE`) with a configured busy timeout (e.g., 5000ms).
  `[@test] ../backend/tests/test_audit_log.py`
- Atomic Head Query and Hash Calculation: The query retrieving the preceding record's `current_hash` and the insertion of the new record execute within the SAME immediate transaction boundary. This guarantees that no other process or thread can read the tail of the chain or insert an entry concurrently, completely preventing race conditions, duplicate `previous_hash` values, or chain fork anomalies.
  `[@test] ../backend/tests/test_audit_log.py`

## Sensitive Data Protection & Redaction

- Financial and security event `details` dictionaries must NEVER contain raw plaintext passwords, Security PINs, encryption keys, or full unmasked account/routing numbers.
  `[@test] ../backend/tests/test_audit_log.py`
- Account numbers in audit details must be masked to the last 4 digits (e.g. `****1001`).
  `[@test] ../backend/tests/test_audit_log.py`

## Integrity Verification Endpoint & Access Protection

- `GET /api/audit/verify` verifies the integrity of the audit chain from genesis to the most recent record.
  `[@test] ../backend/tests/test_audit_log.py`
- Administrative Protection: Access to `GET /api/audit/verify` is restricted to administrative callers via an `X-Admin-Key` header matching `ADMIN_SECRET_KEY` from the server environment. Unauthenticated or invalid requests return HTTP 403 Forbidden.
  `[@test] ../backend/tests/test_audit_log.py`
- Recomputes SHA-256 hashes sequentially, checking that each record's `previous_hash` strictly equals the preceding record's `current_hash`.
  `[@test] ../backend/tests/test_audit_log.py`
- Verifies HMAC-SHA256 signatures for every record against `AUDIT_SECRET_KEY`.
  `[@test] ../backend/tests/test_audit_log.py`
- Returns HTTP 200 with `{ "valid": True, "total_records": N }` when the entire ledger is uncompromised.
  `[@test] ../backend/tests/test_audit_log.py`
- Detects tampered data: If any row's data, hash, or signature is modified, `GET /api/audit/verify` returns `{ "valid": False, "tampered_entry_id": X, "reason": "..." }`.
  `[@test] ../backend/tests/test_audit_log.py`
