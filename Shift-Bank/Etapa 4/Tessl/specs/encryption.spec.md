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

Governed by Researcher Decision D-11 and SEED-4 Items 5 and 6.

> **Architectural Boundary Note:** This mechanism provides application-layer field encryption in depth alongside standard HTTPS/TLS transport security. The backend securely decrypts incoming fields in memory using its server-side private key to execute business validations (balance checks, limit enforcement, MFA evaluation, and recurring scheduling) and re-encrypts sensitive fields with AES-256-GCM for persistent storage at rest.

## Approved Cryptographic Architecture

1. **Hybrid RSA-OAEP-256 / AES-256-GCM**:
   - The backend maintains an RSA key pair (`RSA-OAEP-256`, 2048-bit or higher).
   - The private key is held strictly server-side in secure memory and is NEVER transmitted, logged, or exposed via any API endpoint.
   - The frontend fetches the active public key from `GET /api/crypto/public-key`.
   - For sensitive operations, the client generates an ephemeral 256-bit symmetric session key, encrypts sensitive payload fields using AES-256-GCM (producing ciphertext, 96-bit IV, and 128-bit authentication tag), encrypts the session key using the server public key via RSA-OAEP (with SHA-256), and transmits the combined envelope.
2. **Explicit, Idempotent Legacy Data Migration**:
   - Replaces indefinite plaintext fallback with an explicit, one-time, idempotent startup migration process.
   - The migration operates strictly and exclusively on the isolated database instance, never accessing or modifying prior stage databases.
   - Legacy records lacking encryption are migrated to `enc:v1:<iv>:<tag>:<ciphertext>` format before serving traffic.
3. **Domain Event Payload Encryption**:
   - Sensitive beneficiary coordinates persisted in domain event payloads (e.g. `AchTransferInitiated`) must be stored encrypted using AES-256-GCM (`enc:v1:<iv>:<tag>:<ciphertext>`), identical to storage at rest. [NEW D-11]

## Preexisting Baseline Limitations

- Preexisting Frontend Crypto-Test Incident: The Stage 4 test environment inherits two failing frontend cryptographic unit tests in `frontend/src/__tests__/crypto.test.ts` (documented in `E4_TESSL_INCIDENTES_PREPARACION.md`). Their exact root cause remains unconfirmed. These failures are preserved as an unresolved baseline limitation; they are not classified as resolved, passing, or newly introduced Stage 4 defects. [NEW D-11]
  `[@test] ../frontend/src/__tests__/crypto.test.ts`

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

- `GET /api/crypto/public-key` returns HTTP 200 with the active server public key PEM, algorithm (`RSA-OAEP-256`), `key_id`, and `expires_at` timestamp. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Key Expiration: Active public keys have a bounded validity period (default: 24 hours). The server rotates keys upon expiration while preserving previous keys for a graceful grace period. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Rejection of Expired or Unknown Keys:
  - If incoming payload specifies a `key_id` whose expiration timestamp has passed, the backend rejects the request with HTTP 400 and error code `KEY_EXPIRED`. [INHERITED]
  - If incoming payload specifies an unrecognized or invalid `key_id`, the backend rejects the request with HTTP 400 and error code `INVALID_KEY_ID`. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Frontend caches the public key in memory until its expiration window approaches, refreshing automatically when expired or upon receiving a `KEY_EXPIRED` response. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`

## Application-Layer Field Encryption & Stage 2 API Compatibility

- Dual Payload Format Acceptance: Incoming request payloads on transfer, beneficiary, and recurring endpoints accept BOTH encrypted envelopes (`{"__encrypted__": True, "key_id": "...", ...}`) and standard plaintext strings. Plaintext submissions are accepted for backward compatibility, and are transparently encrypted with AES-256-GCM before database insertion. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- Backend securely decrypts encrypted fields in memory using the server private key before executing transfer validations, limit enforcement, or beneficiary creation. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_transfers.py`
- The system protects all communication with HTTPS/TLS in transit alongside application-layer field encryption. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`

## Encryption at Rest & Event Store Payloads (AES-256-GCM)

- Sensitive banking coordinates (account numbers and routing numbers in `beneficiaries`, `transfers`, `recurring_schedules`, and `domain_events`) are stored encrypted at rest using AES-256-GCM authenticated encryption. [MODIFIED D-11]
  `[@test] ../backend/tests/test_encryption.py`
- Storage format adheres strictly to the canonical prefixed string: `enc:v1:<iv>:<tag>:<ciphertext>`, where IV is 96-bit (12 bytes base64) and tag is 128-bit (16 bytes base64). [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Tamper Detection: Modifying stored ciphertext or altering the authentication tag causes AES-GCM decryption to fail and raises an internal cryptographic integrity error. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Strict Persistence Validation: Any unencrypted plaintext coordinate encountered in storage or event payloads raises an internal data integrity exception; silent indefinite plaintext fallback is forbidden. [MODIFIED D-11]
  `[@test] ../backend/tests/test_encryption.py`

## Explicit, Idempotent, Verifiable Data Migration

- Explicit Migration Procedure: A dedicated migration routine runs during application startup or via a standalone migration command (`python -m backend.app.services.migration_service`). [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Idempotency Guarantee: Re-running migration multiple times produces identical, safe results with zero data re-encryption or corruption. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Post-Migration Verification: Immediately after migration, a verification pass reads all sensitive records and verifies that 100% of values decrypt successfully with the active `ENCRYPTION_KEY`. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Failure Recovery Without Data Loss: Runs inside an atomic database transaction. On failure, rolls back immediately, halts startup with a fatal log, and prevents serving traffic with inconsistent data. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`

## User Interface & Data Masking

- Internal Account Identifiers: Internal user account numbers (`CHK-1001`, `SAV-2001`, `EUR-3001`, `GBP-4001`) returned by `/api/accounts` retain their canonical string representation. [MODIFIED D-01, D-02]
  `[@test] ../backend/tests/test_accounts.py`
- External Banking Coordinates Masking: Third-party account numbers are masked to the last 4 digits (e.g. `****1234` or `****3210`) in audit logs, error messages, and transaction history references. Saved beneficiary and transfer query responses preserve `routing_number` and `account_number` schema fields for authenticated owner operations. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
  `[@test] ../backend/tests/test_ach_transfers.py`
- UI components render masked identifiers seamlessly across account cards, beneficiary dropdowns, transaction lists, and recurring schedules. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`

## Cryptographic Failure Handling & Security Constraints

- Malformed ciphertexts, invalid base64 encodings, or invalid authentication tags return HTTP 422 Unprocessable Entity with error code `INVALID_ENCRYPTED_PAYLOAD`. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Error responses, validation messages, and server log outputs must never include decrypted plaintext values, cryptographic session keys, or private key material. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- If the server storage key (`ENCRYPTION_KEY`) is missing or invalid at startup, the service safely fails fast during initialization. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
- Frontend client bundles and public artifacts must never contain private keys or long-lived symmetric storage keys. [INHERITED]
  `[@test] ../backend/tests/test_encryption.py`
