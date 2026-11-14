---
name: Client-to-Server Field-Level Encryption
description: Secure transmission and storage of sensitive banking identifiers using hybrid RSA-OAEP-256/AES-256-GCM field encryption, AES-256-GCM encryption at rest, and explicit idempotent data migration
targets:
  - ../backend/app/services/crypto_service.py
  - ../backend/app/services/migration_service.py
  - ../backend/app/routers/crypto.py
  - ../backend/app/models.py
  - ../frontend/src/api/crypto.ts
  - ../frontend/src/api/client.ts
---

# Client-to-Server Field-Level Encryption

Defines application-layer field-level encryption for sensitive banking identifiers between the React frontend and FastAPI backend, complemented by authenticated encryption at rest (AES-256-GCM) in the SQLite database and an explicit, idempotent migration process for legacy records.

> **Architectural Boundary Note:** This mechanism provides application-layer field encryption in depth alongside standard HTTPS/TLS transport security. The backend securely decrypts incoming fields in memory using its server-side private key to execute business validations (balance checks, limit enforcement, MFA evaluation, and recurring scheduling) and re-encrypts sensitive fields with AES-256-GCM for persistent storage at rest.

## Approved Cryptographic Architecture

1. **Hybrid RSA-OAEP-256 / AES-256-GCM**:
   - The backend maintains an RSA key pair (`RSA-OAEP-256`, 2048-bit or higher).
   - The private key is held strictly server-side in secure memory and is NEVER transmitted, logged, or exposed via any API endpoint.
   - The frontend fetches the active public key from `GET /api/crypto/public-key`.
   - For sensitive operations, the client generates an ephemeral 256-bit symmetric session key, encrypts sensitive payload fields using AES-256-GCM (producing ciphertext, 96-bit IV, and 128-bit authentication tag), encrypts the session key using the server public key via RSA-OAEP (with SHA-256), and transmits the combined envelope.
2. **Explicit, Idempotent Legacy Data Migration**:
   - Replaces indefinite plaintext fallback with an explicit, one-time, idempotent startup migration process.
   - The migration operates strictly and exclusively on the isolated Stage 3 database instance, never accessing or modifying Stage 1 or Stage 2 databases.
   - Legacy records lacking encryption are migrated to `enc:v1:<iv>:<tag>:<ciphertext>` format before serving traffic.

## Data Contract

```python
class PublicKeyResponse(BaseModel):
    key_id: str
    algorithm: str  # "RSA-OAEP-256"
    public_key: str  # PEM-encoded public key
    expires_at: datetime

class EncryptedEnvelope(BaseModel):
    ciphertext: str       # Base64-encoded encrypted data
    encrypted_key: str    # Base64-encoded session key encrypted with server public key
    iv: str               # Base64-encoded initialization vector / nonce (96-bit for AES-GCM)
    tag: str              # Base64-encoded authentication tag (128-bit)
    key_id: str           # Identifier of the server public key used

class EncryptedFieldPayload(BaseModel):
    __encrypted__: bool = True
    key_id: str
    encrypted_key: str
    iv: str
    ciphertext: str
    tag: str

class MigrationResult(BaseModel):
    success: bool
    migrated_records: int
    skipped_records: int
    verified_records: int
    error_message: Optional[str] = None
```

## Public Key Management & Key Expiration

- `GET /api/crypto/public-key` returns HTTP 200 with the active server public key PEM, algorithm (`RSA-OAEP-256`), `key_id`, and `expires_at` timestamp.
  `[@test] ../backend/tests/test_encryption.py`
- Key Expiration: Active public keys have a bounded validity period (default: 24 hours). The server rotates keys upon expiration while preserving previous keys for a graceful grace period.
  `[@test] ../backend/tests/test_encryption.py`
- Rejection of Expired or Unknown Keys:
  - If incoming payload specifies a `key_id` whose expiration timestamp has passed, the backend rejects the request with HTTP 400 and error code `KEY_EXPIRED`.
  - If incoming payload specifies an unrecognized or invalid `key_id`, the backend rejects the request with HTTP 400 and error code `INVALID_KEY_ID`.
  `[@test] ../backend/tests/test_encryption.py`
- Frontend caches the public key in memory until its expiration window approaches, refreshing automatically when expired or upon receiving a `KEY_EXPIRED` response.
  `[@test] ../backend/tests/test_encryption.py`

## Application-Layer Field Encryption & Stage 2 API Compatibility

- Dual Payload Format Acceptance: Incoming request payloads on transfer, beneficiary, and recurring endpoints accept BOTH encrypted envelopes (`{"__encrypted__": True, "key_id": "...", ...}`) and standard plaintext strings. Plaintext submissions are accepted for backward compatibility with existing Stage 1 and Stage 2 test suites, and are transparently encrypted with AES-256-GCM before database insertion.
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Backend securely decrypts encrypted fields in memory using the server private key before executing transfer validations, limit enforcement, or beneficiary creation.
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_transfers.py`
- The system protects all communication with HTTPS/TLS in transit alongside application-layer field encryption.
  `[@test] ../backend/tests/test_encryption.py`

## Encryption at Rest (AES-256-GCM)

- Sensitive banking coordinates (account numbers and routing numbers in `beneficiaries`, `transfers`, and `recurring_schedules`) are stored encrypted at rest using AES-256-GCM authenticated encryption.
  `[@test] ../backend/tests/test_encryption.py`
- Storage format adheres strictly to the canonical prefixed string: `enc:v1:<iv>:<tag>:<ciphertext>`, where IV is 96-bit (12 bytes base64) and tag is 128-bit (16 bytes base64).
  `[@test] ../backend/tests/test_encryption.py`
- Tamper Detection: Modifying stored ciphertext or altering the authentication tag causes AES-GCM decryption to fail and raises an internal cryptographic integrity error.
  `[@test] ../backend/tests/test_encryption.py`
- Strict Persistence Validation: Once migration is executed, any unencrypted plaintext coordinate encountered in storage raises an internal data integrity exception; silent indefinite plaintext fallback is forbidden.
  `[@test] ../backend/tests/test_encryption.py`

## Explicit, Idempotent, Verifiable Data Migration

- Explicit Migration Procedure: A dedicated migration routine runs during Stage 3 application startup or via a standalone migration command (`python -m backend.app.services.migration_service`).
  `[@test] ../backend/tests/test_encryption.py`
- Strict Stage 3 Database Isolation: The migration executes exclusively against the local Stage 3 SQLite database (`shift_bank.db` / `/app/data/shift_bank.db`). It must NEVER read, modify, or connect to Stage 1 or Stage 2 databases or repository artifacts.
  `[@test] ../backend/tests/test_encryption.py`
- Idempotency Guarantee: The migration inspects each record in `beneficiaries`, `transfers`, and `recurring_schedules`:
  - Records already formatted with `enc:v1:` prefix are preserved without modification (`skipped_records += 1`).
  - Only records with legacy plaintext coordinates are encrypted with AES-256-GCM and updated (`migrated_records += 1`).
  - Re-running the migration multiple times produces identical, safe results with zero data re-encryption or corruption.
  `[@test] ../backend/tests/test_encryption.py`
- Post-Migration Verification: Immediately after migration, a verification pass reads all sensitive records and verifies that 100% of values decrypt successfully with the active `ENCRYPTION_KEY`.
  `[@test] ../backend/tests/test_encryption.py`
- Failure Recovery Without Data Loss:
  - The migration runs inside an atomic database transaction.
  - If any error occurs during migration or post-verification, the transaction is rolled back immediately, leaving the database in its original state without data loss.
  - In the event of a migration failure, backend startup halts with a fatal initialization log, preventing the system from serving traffic with inconsistent data.
  `[@test] ../backend/tests/test_encryption.py`

## User Interface & Data Masking

- Internal Account Identifiers: Internal user account numbers (`CHK-1001`, `SAV-2001`) returned by `/api/accounts` retain their canonical string representation to guarantee contract compatibility with existing Stage 1 and Stage 2 test suites and UI components.
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_accounts.py`
- External Banking Coordinates Masking: Third-party account numbers are masked to the last 4 digits (e.g. `****1234` or `****3210`) in audit logs, error messages, and transaction history references. Saved beneficiary and transfer query responses preserve `routing_number` and `account_number` schema fields for authenticated owner operations.
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- UI components render masked identifiers seamlessly across account cards, beneficiary dropdowns, transaction lists, and recurring schedules.
  `[@test] ../backend/tests/test_encryption.py`

## Cryptographic Failure Handling & Security Constraints

- Malformed ciphertexts, invalid base64 encodings, or invalid authentication tags return HTTP 422 Unprocessable Entity with error code `INVALID_ENCRYPTED_PAYLOAD`.
  `[@test] ../backend/tests/test_encryption.py`
- Error responses, validation messages, and server log outputs must never include decrypted plaintext values, cryptographic session keys, or private key material.
  `[@test] ../backend/tests/test_encryption.py`
- If the server storage key (`ENCRYPTION_KEY`) is missing or invalid at startup, the service safely fails fast during initialization.
  `[@test] ../backend/tests/test_encryption.py`
- Frontend client bundles and public artifacts must never contain private keys or long-lived symmetric storage keys.
  `[@test] ../backend/tests/test_encryption.py`
