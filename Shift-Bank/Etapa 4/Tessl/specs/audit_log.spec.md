---
name: Cryptographic Audit Ledger
description: Tamper-evident, append-only SQLite audit log with SHA-256 hash chaining and HMAC-SHA256 signatures for financial transactions, conversions, and security events
targets:
  - ../backend/app/models.py
  - ../backend/app/services/audit_service.py
  - ../backend/app/routers/audit.py
---

# Cryptographic Audit Ledger

Provides an append-only, tamper-evident audit ledger capturing all financial transfers, currency conversions, and authentication/security events. Each ledger entry is cryptographically linked to the preceding entry using SHA-256 hash chaining and signed with HMAC-SHA256.

Governed by Researcher Decisions D-05, D-06, D-09, and D-11 and SEED-4 Items 3, 5, and 6.

## Data Contract

```python
class AuditLogEntry(BaseModel):
    id: int
    event_id: str                      # UUID v4 unique identifier
    timestamp: datetime                # UTC ISO-8601 timestamp
    event_type: str                    # e.g., "transfer_internal", "currency_conversion", "transfer_ach", "mfa_pin", "limit_breach"
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

- Dedicated Audit Table: An `audit_logs` SQLite table stores all audit events sequentially and immutably. [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`
- Immutability Enforcement: Direct `UPDATE` and `DELETE` operations on `audit_logs` are prevented at the database and ORM layers. Any attempt raises an internal audit integrity exception. [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`
- Genesis Record: Initial entry uses `previous_hash` equal to 64 hexadecimal zeros (`0000000000000000000000000000000000000000000000000000000000000000`). [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`
- SHA-256 Hash Chaining: Each record computes `current_hash = SHA256(previous_hash + event_id + timestamp_iso + event_type + str(actor_id) + status + canonical_json_details)`. [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`
- HMAC-SHA256 Signature: Each entry includes an HMAC-SHA256 signature calculated over `current_hash` using `AUDIT_SECRET_KEY`: `HMAC_SHA256(audit_secret_key, current_hash)`. [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`
- Key Protection: The audit secret key is loaded strictly from environment variable `AUDIT_SECRET_KEY` and never exposed or logged. Missing key at startup halts initialization. [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`

## Separation from Domain Event Store

- Independent Architecture: The `audit_logs` ledger is completely independent from the `domain_events` table. Domain events represent authoritative financial state transitions; audit records provide security, compliance, and regulatory traceability. [NEW D-05, D-11]
  `[@test] ../backend/tests/test_audit_log.py`
- Replay Isolation: Replaying domain events or rebuilding CQRS read projections must NEVER generate new audit records or re-execute audit verification. [NEW D-06, D-11]
  `[@test] ../backend/tests/test_audit_log.py`

## Audited Event Types

- Currency Conversions: Emits audit events for every conversion attempt:
  - `currency_conversion` with `status="SUCCESS"` upon successful atomic conversion, recording operation ID, source currency/amount, destination currency/amount, and applied rate factors. [NEW D-11]
  - `currency_conversion` with `status="FAILURE"` upon failed/rejected conversion (balance, limit, or version conflict). [NEW D-11]
  `[@test] ../backend/tests/test_audit_log.py`
- Internal Transfers: Emits `transfer_internal` (`status="SUCCESS"` or `status="FAILURE"`). [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_transfers.py`
- External ACH Transfers: Emits `transfer_ach_initiated`, `transfer_ach_settled`, and `transfer_ach_failed`. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Recurring Payments: Emits schedule lifecycle events (`recurring_schedule_created`, `recurring_schedule_paused`, `recurring_schedule_resumed`, `recurring_schedule_cancelled`) and `recurring_payment_executed` (`status="SUCCESS"` or `status="FAILURE"`). [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_recurring_payments.py`
- MFA & Security Events: Emits `mfa_verified`, `mfa_attempt_failed`, `mfa_locked`, and `mfa_lockout_rejected`. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_mfa.py`
- Transfer Limit Breaches: Emits `limit_breach` with `status="FAILURE"` when an operation violates USD-equivalent limits. [MODIFIED D-07, D-11]
  `[@test] ../backend/tests/test_audit_log.py`
  `[@test] ../backend/tests/test_transfer_limits.py`

## Rollback Consistency & Transaction Isolation

- Failure Preservation: If a financial transfer, conversion, limit check, or security operation fails, the failure audit entry (`status="FAILURE"`) is committed in an autonomous transaction after business rollback. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
- Success Atomicity: Successful business operations commit domain events, CQRS projections, and audit records atomically in the same SQLite transaction. [MODIFIED D-06, D-11]
  `[@test] ../backend/tests/test_audit_log.py`
- Fail-Closed Audit Guarantee: Failure to record an audit entry rolls back the primary banking transaction. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`

## Multi-Process Concurrency Safety & SQLite File Locking

- Multi-Process Safety: Chain calculation and record insertion are serialized at the database engine level using SQLite exclusive write transactions (`BEGIN IMMEDIATE`) with busy timeout (5000ms). [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`
- Atomic Head Query: Querying preceding `current_hash` and inserting new record execute within the same immediate transaction boundary, preventing chain forks. [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`

## Protected Ledger Verification Endpoint

- Ingress-Protected Verification: `GET /api/audit/verify` verifies full chain integrity from genesis to head, returning `AuditVerificationResponse`. Protected by `X-Admin-Key` header validated against `ADMIN_SECRET_KEY`. [INHERITED]
  `[@test] ../backend/tests/test_audit_log.py`

## Sensitive Data Protection & Redaction

- Financial and security event `details` dictionaries must NEVER contain raw plaintext passwords, Security PINs, encryption keys, or full unmasked account/routing numbers. [INHERITED D-11]
  `[@test] ../backend/tests/test_audit_log.py`
