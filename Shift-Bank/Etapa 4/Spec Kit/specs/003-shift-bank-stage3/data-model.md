# Data Model: Shift Bank Stage 3 — Security Hardening, Audit Integrity, and Safe Migration

This document defines the SQLite database schema, field-level encryption representation, audit ledger structure, entity models, state machines, and safe legacy migration strategy for Shift Bank Stage 3.

---

## 1. Database Schema & Persistence Strategy (SQLite)

### 1.1. Inherited Baseline Tables & At-Rest Encryption Representation
In Stage 3, the database tables inherited from Stage 2 (`accounts`, `transfers`, `beneficiaries`, `limits`, `recurring_schedules`) maintain their relational schema, while sensitive fields are transformed into authenticated ciphertext strings at rest.

#### Ciphertext Envelope Format
All encrypted text columns store a standardized authenticated ciphertext envelope string:
```text
enc:v1:<iv_base64>:<ciphertext_and_tag_base64>
```
- Algorithm: AES-256-GCM (128-bit authentication tag, 96-bit initialization vector).
- Key: Server-held persistent storage key (`BANK_STORAGE_KEY`, 256-bit symmetric key).
- Envelope Validation: A valid encrypted field MUST start with `enc:v1:`, have exactly two colon separators, and contain valid base64-encoded IV and ciphertext/tag components.
- Identification: Unencrypted legacy records lack the `enc:v1:` prefix, allowing reliable multi-field detection during startup migration.

---

### 1.2. Evolved Schema Definitions

#### Table: `accounts`
Stores customer bank accounts. Balance is stored as authenticated ciphertext at rest, decrypting into Python `Decimal` in memory.

```sql
CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,                     -- 'acc_checking', 'acc_savings'
    name TEXT UNIQUE NOT NULL,               -- 'Checking Account', 'Savings Account'
    balance TEXT NOT NULL,                  -- Ciphertext: enc:v1:... (Decimal string in memory)
    currency TEXT NOT NULL DEFAULT 'COP'     -- 'COP' (Colombian Pesos)
);
```

#### Table: `transfers`
Stores internal and external ACH transfers. Sensitive financial amounts, recipient names, bank names, routing numbers, and account numbers are encrypted at rest.

```sql
CREATE TABLE IF NOT EXISTS transfers (
    id TEXT PRIMARY KEY,                     -- 'tr_uuid'
    source_account_id TEXT NOT NULL,         -- 'acc_checking', 'acc_savings'
    destination_account_id TEXT,             -- 'acc_savings', 'acc_checking' (NULL for ACH)
    amount TEXT NOT NULL,                    -- Ciphertext: enc:v1:... (Decimal string in memory)
    status TEXT NOT NULL,                    -- 'COMPLETED', 'PENDING_MFA', 'PENDING', 'SETTLED', 'FAILED', 'EXPIRED'
    created_at TEXT NOT NULL,                -- ISO-8601 UTC timestamp
    expires_at TEXT,                         -- ISO-8601 UTC timestamp (nullable)
    transfer_type TEXT NOT NULL DEFAULT 'INTERNAL', -- 'INTERNAL' or 'ACH'
    recipient_name TEXT,                     -- Ciphertext: enc:v1:... (or NULL for internal)
    bank_name TEXT,                          -- Ciphertext: enc:v1:... (or NULL for internal)
    routing_number TEXT,                     -- Ciphertext: enc:v1:... (or NULL for internal)
    account_number TEXT,                     -- Ciphertext: enc:v1:... (or NULL for internal)
    settled_at TEXT,                         -- ISO-8601 UTC timestamp (nullable)
    failed_at TEXT,                          -- ISO-8601 UTC timestamp (nullable)
    refunded_at TEXT,                        -- ISO-8601 UTC timestamp (nullable)
    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
    FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
);
```

#### Table: `beneficiaries`
Stores saved external ACH recipients. Recipient identity, bank names, routing numbers, and account numbers are encrypted at rest.

```sql
CREATE TABLE IF NOT EXISTS beneficiaries (
    id TEXT PRIMARY KEY,                     -- 'ben_uuid'
    user_id TEXT NOT NULL DEFAULT 'user_mock_001',
    name TEXT NOT NULL,                      -- Ciphertext: enc:v1:...
    bank_name TEXT NOT NULL,                 -- Ciphertext: enc:v1:...
    routing_number TEXT NOT NULL,            -- Ciphertext: enc:v1:...
    account_number TEXT NOT NULL,            -- Ciphertext: enc:v1:...
    created_at TEXT NOT NULL                 -- ISO-8601 UTC timestamp
);
```

#### Table: `limits`
Stores user-configurable dynamic limits. Both per-transfer and daily limits are stored as authenticated ciphertext at rest, preserving exact arithmetic when evaluated in Python `Decimal`.

```sql
CREATE TABLE IF NOT EXISTS limits (
    id TEXT PRIMARY KEY,                     -- 'lim_default'
    user_id TEXT NOT NULL UNIQUE DEFAULT 'user_mock_001',
    per_transfer_limit TEXT NOT NULL DEFAULT '5000000.00', -- Ciphertext: enc:v1:...
    daily_limit TEXT NOT NULL DEFAULT '10000000.00',        -- Ciphertext: enc:v1:...
    updated_at TEXT NOT NULL                 -- ISO-8601 UTC timestamp
);
```

#### Table: `recurring_schedules`
Stores automated recurring transfer instructions. Amounts and sensitive recipient details are encrypted at rest.

```sql
CREATE TABLE IF NOT EXISTS recurring_schedules (
    id TEXT PRIMARY KEY,                     -- 'rec_uuid'
    user_id TEXT NOT NULL DEFAULT 'user_mock_001',
    transfer_type TEXT NOT NULL,             -- 'INTERNAL' or 'ACH'
    source_account_id TEXT NOT NULL,         -- 'acc_checking', 'acc_savings'
    destination_account_id TEXT,             -- Target account ID (NULL for ACH)
    amount TEXT NOT NULL,                    -- Ciphertext: enc:v1:...
    frequency TEXT NOT NULL,                 -- 'DAILY', 'WEEKLY', 'MONTHLY'
    status TEXT NOT NULL,                    -- 'ACTIVE', 'PAUSED', 'CANCELLED', 'PENDING_MFA', 'EXPIRED'
    next_due_date TEXT NOT NULL,             -- ISO-8601 UTC date
    recipient_name TEXT,                     -- Ciphertext: enc:v1:...
    bank_name TEXT,                          -- Ciphertext: enc:v1:...
    routing_number TEXT,                     -- Ciphertext: enc:v1:...
    account_number TEXT,                     -- Ciphertext: enc:v1:...
    last_executed_at TEXT,                   -- ISO-8601 UTC timestamp (nullable)
    mfa_expires_at TEXT,                     -- ISO-8601 UTC timestamp (nullable)
    created_at TEXT NOT NULL,                -- ISO-8601 UTC timestamp
    FOREIGN KEY (source_account_id) REFERENCES accounts(id),
    FOREIGN KEY (destination_account_id) REFERENCES accounts(id)
);
```

---

### 1.3. New Table: `audit_logs` & Contiguous Sequencing Architecture (E3-AUD-01)
Stores the append-only, cryptographically chained transaction audit trail.

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY,                  -- Strictly contiguous sequence: 1, 2, 3...
    timestamp TEXT NOT NULL,                 -- ISO-8601 UTC timestamp (e.g. '2026-11-15T20:00:00.000000Z')
    event_type TEXT NOT NULL,                -- 'TRANSFER_CREATED', 'TRANSFER_COMPLETED', 'MFA_CHALLENGED',
                                             -- 'MFA_VERIFIED', 'MFA_FAILED', 'ACH_PENDING', 'ACH_SETTLED',
                                             -- 'ACH_FAILED', 'ACH_REFUNDED', 'LIMIT_UPDATED',
                                             -- 'RECURRING_CREATED', 'RECURRING_EXECUTED', 'RECURRING_FAILED'
    actor_id TEXT NOT NULL,                  -- 'user_mock_001', 'system_scheduler'
    resource_id TEXT,                        -- Resource ID: 'tr_xxx', 'lim_xxx', 'sch_xxx', 'ben_xxx'
    payload_digest TEXT NOT NULL,            -- SHA-256 digest of canonical non-sensitive payload JSON
    previous_hash TEXT NOT NULL,             -- record_hmac of entry (id - 1), or '0'*64 for genesis (id = 1)
    record_hmac TEXT NOT NULL                -- HMAC-SHA256(AUDIT_SIGNING_KEY, previous_hash || id || timestamp || event_type || actor_id || resource_id || payload_digest)
);

-- Database-level immutability enforcement triggers
CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_update
BEFORE UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'Audit records are immutable and cannot be updated');
END;

CREATE TRIGGER IF NOT EXISTS trg_prevent_audit_delete
BEFORE DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'Audit records are immutable and cannot be deleted');
END;
```

#### Contiguous Monotonic Sequence Allocation (Addressing SQLite AUTOINCREMENT Gaps)
SQLite's native `AUTOINCREMENT` keyword does NOT guarantee gap-free sequences because rolled-back transactions consume sequence IDs without recycling them. To ensure strictly contiguous gap-free sequence numbers ($1, 2, 3, \dots, N$):
1. All financial mutations and audit writes execute inside exclusive transactions (`BEGIN IMMEDIATE;`).
2. The sequence number and predecessor hash are obtained directly from the committed ledger within the active write lock:
   ```sql
   SELECT COALESCE(MAX(id), 0) + 1,
          COALESCE((SELECT record_hmac FROM audit_logs WHERE id = (SELECT MAX(id) FROM audit_logs)),
                   '0000000000000000000000000000000000000000000000000000000000000000')
   FROM audit_logs;
   ```
3. Because `BEGIN IMMEDIATE` serializes write transactions, candidate sequence numbers are only committed when the entire transaction succeeds. If a transaction aborts or encounters an error, candidate numbers are discarded without leaving sequence gaps.

#### External Trusted Checkpoints (Tail Truncation Detection)
- **Problem**: Mathematical chaining detects modification, insertion, deletion, and reordering, but cannot detect deletion of trailing records ($N - k \dots N$) from a local database without an external anchor, because any prefix of a valid hash chain is mathematically valid.
- **Checkpoint Structure**: An external trusted checkpoint is a signed or externally stored tuple:
  $$\text{Checkpoint} = \big(\text{checkpoint\_sequence},\, \text{checkpoint\_hash},\, \text{checkpoint\_timestamp}\big)$$
- **Obtaining Checkpoints**:
  1. An external operational process, monitoring job, or administrative audit export periodically queries the audit head:
     ```sql
     SELECT id, record_hmac, timestamp FROM audit_logs ORDER BY id DESC LIMIT 1;
     ```
  2. The resulting tuple is persisted to a separate, write-restricted external storage medium or monitoring service.
- **Validating Checkpoints (`GET /api/audit/verify`)**:
  When verification is invoked with query parameters `expected_head_hash` and `expected_count`:
  1. The verifier first validates internal chain integrity from sequence 1 to current max sequence $M$.
  2. If $M < \text{expected\_count}$, the verifier flags an integrity error: **Tail Truncation Detected** (the database is missing records present in the trusted checkpoint).
  3. If $M == \text{expected\_count}$ and latest hash $\ne \text{expected\_head\_hash}$, the verifier flags: **Tail Tampering / Divergence Detected**.
  4. If $M > \text{expected\_count}$, the verifier checks that record at `id == expected_count` matches `record_hmac == expected_head_hash` (verifying the checkpoint is a valid ancestor of the current head).

---

## 2. Safe, Idempotent Legacy Plaintext Migration Strategy (FR-013)

### 2.1. Migration Scope & Comprehensive Entity Scanning
The migration process executes during `init_db()` upon application startup. It inspects all sensitive fields across all five entities, handling mixed states, nullable fields, and corrupted ciphertext envelopes.

```python
import sqlite3
from typing import Tuple

def validate_or_encrypt_field(val: str | None, field_name: str, row_id: str, storage_key: bytes) -> Tuple[str | None, bool]:
    """
    Validates an existing field value.
    - If None: returns (None, False).
    - If already encrypted (starts with 'enc:v1:'): validates structure; raises ValueError if corrupted.
    - If plaintext: encrypts using storage_key and returns (ciphertext, True).
    """
    if val is None:
        return None, False

    if val.startswith("enc:v1:"):
        parts = val.split(":")
        if len(parts) != 4 or not parts[2] or not parts[3]:
            raise ValueError(f"Corrupted ciphertext envelope in {field_name} for row {row_id}")
        return val, False

    # Value is plaintext; convert to encrypted envelope
    encrypted = encrypt_at_rest(val, storage_key)
    return encrypted, True

def migrate_legacy_plaintext_records(conn: sqlite3.Connection, storage_key: bytes) -> int:
    """
    Safely and idempotently converts legacy Stage 2 plaintext records to encrypted storage.
    Performs complete entity validation. Rolls back atomically on any failure.
    """
    cursor = conn.cursor()
    cursor.execute("BEGIN IMMEDIATE;")
    try:
        migrated_fields = 0

        # 1. Accounts (balance)
        cursor.execute("SELECT id, balance FROM accounts;")
        for acc_id, balance in cursor.fetchall():
            new_val, changed = validate_or_encrypt_field(balance, "accounts.balance", acc_id, storage_key)
            if changed:
                cursor.execute("UPDATE accounts SET balance = ? WHERE id = ?;", (new_val, acc_id))
                migrated_fields += 1

        # 2. Dynamic Limits (per_transfer_limit, daily_limit)
        cursor.execute("SELECT id, per_transfer_limit, daily_limit FROM limits;")
        for lim_id, per_tr, daily in cursor.fetchall():
            new_per, ch_per = validate_or_encrypt_field(per_tr, "limits.per_transfer_limit", lim_id, storage_key)
            new_day, ch_day = validate_or_encrypt_field(daily, "limits.daily_limit", lim_id, storage_key)
            if ch_per or ch_day:
                cursor.execute("UPDATE limits SET per_transfer_limit = ?, daily_limit = ? WHERE id = ?;",
                               (new_per, new_day, lim_id))
                migrated_fields += int(ch_per) + int(ch_day)

        # 3. Beneficiaries (name, bank_name, routing_number, account_number)
        cursor.execute("SELECT id, name, bank_name, routing_number, account_number FROM beneficiaries;")
        for ben_id, name, bank_name, routing, acc_num in cursor.fetchall():
            new_name, ch_name = validate_or_encrypt_field(name, "beneficiaries.name", ben_id, storage_key)
            new_bank, ch_bank = validate_or_encrypt_field(bank_name, "beneficiaries.bank_name", ben_id, storage_key)
            new_rout, ch_rout = validate_or_encrypt_field(routing, "beneficiaries.routing_number", ben_id, storage_key)
            new_acc, ch_acc = validate_or_encrypt_field(acc_num, "beneficiaries.account_number", ben_id, storage_key)
            if any([ch_name, ch_bank, ch_rout, ch_acc]):
                cursor.execute(
                    "UPDATE beneficiaries SET name = ?, bank_name = ?, routing_number = ?, account_number = ? WHERE id = ?;",
                    (new_name, new_bank, new_rout, new_acc, ben_id)
                )
                migrated_fields += sum([ch_name, ch_bank, ch_rout, ch_acc])

        # 4. Transfers (amount, recipient_name, bank_name, routing_number, account_number)
        cursor.execute("SELECT id, amount, recipient_name, bank_name, routing_number, account_number FROM transfers;")
        for tr_id, amount, rec_name, bank_name, routing, acc_num in cursor.fetchall():
            new_amt, ch_amt = validate_or_encrypt_field(amount, "transfers.amount", tr_id, storage_key)
            new_rec, ch_rec = validate_or_encrypt_field(rec_name, "transfers.recipient_name", tr_id, storage_key)
            new_bank, ch_bank = validate_or_encrypt_field(bank_name, "transfers.bank_name", tr_id, storage_key)
            new_rout, ch_rout = validate_or_encrypt_field(routing, "transfers.routing_number", tr_id, storage_key)
            new_acc, ch_acc = validate_or_encrypt_field(acc_num, "transfers.account_number", tr_id, storage_key)
            if any([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc]):
                cursor.execute(
                    "UPDATE transfers SET amount = ?, recipient_name = ?, bank_name = ?, routing_number = ?, account_number = ? WHERE id = ?;",
                    (new_amt, new_rec, new_bank, new_rout, new_acc, tr_id)
                )
                migrated_fields += sum([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc])

        # 5. Recurring Schedules (amount, recipient_name, bank_name, routing_number, account_number)
        cursor.execute("SELECT id, amount, recipient_name, bank_name, routing_number, account_number FROM recurring_schedules;")
        for sch_id, amount, rec_name, bank_name, routing, acc_num in cursor.fetchall():
            new_amt, ch_amt = validate_or_encrypt_field(amount, "recurring_schedules.amount", sch_id, storage_key)
            new_rec, ch_rec = validate_or_encrypt_field(rec_name, "recurring_schedules.recipient_name", sch_id, storage_key)
            new_bank, ch_bank = validate_or_encrypt_field(bank_name, "recurring_schedules.bank_name", sch_id, storage_key)
            new_rout, ch_rout = validate_or_encrypt_field(routing, "recurring_schedules.routing_number", sch_id, storage_key)
            new_acc, ch_acc = validate_or_encrypt_field(acc_num, "recurring_schedules.account_number", sch_id, storage_key)
            if any([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc]):
                cursor.execute(
                    "UPDATE recurring_schedules SET amount = ?, recipient_name = ?, bank_name = ?, routing_number = ?, account_number = ? WHERE id = ?;",
                    (new_amt, new_rec, new_bank, new_rout, new_acc, sch_id)
                )
                migrated_fields += sum([ch_amt, ch_rec, ch_bank, ch_rout, ch_acc])

        conn.commit()
        return migrated_fields
    except Exception:
        conn.rollback()
        raise
```

---

## 3. Entity Models & Pydantic Schemas

### 3.1. Cryptographic Envelopes & Audit Schemas (`backend/src/models.py`)

```python
from pydantic import BaseModel, Field

class CryptographicEnvelope(BaseModel):
    """Client-originated encrypted payload wrapper."""
    encrypted_key: str = Field(..., description="Base64 encoded RSA-wrapped ephemeral AES key")
    iv: str = Field(..., description="Base64 encoded 12-byte initialization vector")
    ciphertext: str = Field(..., description="Base64 encoded AES-256-GCM ciphertext")
    tag: str = Field(..., description="Base64 encoded 16-byte authentication tag")

class AuditRecordResponse(BaseModel):
    id: int
    timestamp: str
    event_type: str
    actor_id: str
    resource_id: str | None
    payload_digest: str
    previous_hash: str
    record_hmac: str

class AuditVerificationResponse(BaseModel):
    is_valid: bool
    verified_records: int
    latest_sequence: int
    latest_hash: str
    details: str
    broken_sequence: int | None = None
    tail_truncation_detected: bool = False
    expected_head: str | None = None

class HealthResponse(BaseModel):
    status: str = "healthy"
    database: str = "connected"
    scheduler_active: bool = True
    crypto_keys_loaded: bool = True
```

---

## 4. State Machines & Lifecycle Transitions

### 4.1. Transfer Status Machine (Verified against Stage 2 Contract)
| Status | Meaning | Next Valid States | Trigger |
|---|---|---|---|
| `COMPLETED` | Successful internal transfer; funds transferred | Terminal state | Successful execution / MFA verification |
| `PENDING_MFA` | Step-up authentication required ($\ge \text{COP } 1,000,000.00$) | `COMPLETED`, `EXPIRED`, `FAILED` | Initial creation exceeding MFA threshold |
| `PENDING` | ACH transfer initiated; awaiting settlement | `SETTLED`, `FAILED` | Valid ACH creation without MFA or upon MFA completion |
| `SETTLED` | ACH transfer settled after 10-second delay | Terminal state | Background scheduler settlement sweep |
| `FAILED` | Transfer rejected or simulated ACH failure | Terminal state | Simulated failure or authorization error |
| `EXPIRED` | MFA window expired (> 300 seconds) | Terminal state | Expiration sweep or timeout |

*Note on Refunds*: In Stage 2, ACH refunds are recorded through the `refunded_at` timestamp on transfers with status `FAILED`; there is no distinct `REFUNDED` status column value in the database.

### 4.2. Recurring Schedule Status Machine (Verified against Stage 2 Contract)
| Status | Meaning | Next Valid States | Trigger |
|---|---|---|---|
| `ACTIVE` | Schedule running; eligible for execution when due | `PAUSED`, `CANCELLED` | Creation or resumption |
| `PAUSED` | Schedule suspended by customer | `ACTIVE`, `CANCELLED` | Customer action |
| `CANCELLED` | Schedule terminated permanently | Terminal state | Customer action |
| `PENDING_MFA` | Sensitive schedule creation awaiting MFA | `ACTIVE`, `EXPIRED` | Initial creation $\ge \text{COP } 1,000,000.00$ |
| `EXPIRED` | MFA authorization expired | Terminal state | Timeout sweep |
