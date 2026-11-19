## Purpose

Protect sensitive banking identifiers in transit and at rest while retaining authorized backend access needed to carry out the simulated banking operations.

## ADDED Requirements

### Requirement: Authenticated protection of sensitive banking data
The system MUST protect account numbers, routing numbers, stored beneficiary banking details, ACH recipient banking details, and other designated sensitive banking identifiers using authenticated encryption at rest and HTTPS in transit between the browser and authorized backend. The backend MUST be able to decrypt authorized values for banking operations. The system MUST NOT claim zero-knowledge end-to-end encryption. Ciphertext integrity MUST be verified before use, and authentication or decryption failures MUST fail closed without returning or using corrupted plaintext.

#### Scenario: Authorized banking operation uses protected identifier
- **WHEN** an authorized operation needs a stored beneficiary account or routing number
- **THEN** the backend decrypts and integrity-verifies that value for the operation while storage remains encrypted

#### Scenario: Tampered ciphertext is rejected
- **WHEN** an encrypted value fails authenticated integrity verification
- **THEN** the system refuses to use or disclose it, records a safe operational failure, and does not fall back to plaintext

#### Scenario: Browser request requires HTTPS
- **WHEN** the browser sends or receives sensitive banking data
- **THEN** the exchange uses HTTPS and the service does not expose an HTTP plaintext fallback

### Requirement: Secure key provisioning and lifecycle
Encryption keys MUST be provisioned externally to application source and database files, separated from encrypted records, access-controlled, and versioned sufficiently to identify the key needed for decryption. Key rotation MUST preserve authorized access to existing records until a verified re-encryption completes. Missing, invalid, obsolete, or unavailable required keys MUST prevent affected reads and writes from silently proceeding with plaintext or a different key.

#### Scenario: Required key is unavailable
- **WHEN** the application starts or accesses a record and its required key is missing or unavailable
- **THEN** the affected protected operation fails safely and no plaintext fallback occurs

#### Scenario: Invalid or obsolete key cannot decrypt
- **WHEN** a supplied key is invalid or cannot authenticate a record encrypted under a prior key version
- **THEN** the record is not returned or modified and the failure is reported without exposing sensitive values

### Requirement: Safe migration of inherited sensitive records
Migration of inherited SQLite records MUST preserve every banking record and its relationships, encrypt all in-scope values, and be restart-safe and idempotent. A migration MUST commit only after verification succeeds; any failure MUST roll back its incomplete changes and leave the source data recoverable. Startup and normal operation MUST NOT expose an insecure plaintext fallback during or after migration. Restarted systems MUST recognize completed migrations and remain compatible with existing banking API behavior.

#### Scenario: Migration completes and is repeated
- **WHEN** a migration encrypts inherited sensitive records successfully and is invoked again
- **THEN** all original records remain available through authorized operations, stored sensitive values remain encrypted, and no record is duplicated or corrupted

#### Scenario: Migration failure rolls back
- **WHEN** encryption, verification, or persistence fails before migration completion
- **THEN** the migration rolls back its incomplete changes, preserves a recoverable consistent database, and blocks unsafe use of unprotected fields

#### Scenario: Application restarts after migration
- **WHEN** the application restarts after a completed migration using the provisioned key material
- **THEN** it reads the protected records and existing banking APIs continue to provide their inherited behavior

### Requirement: Preserve sensitive-data API compatibility
Protection MUST preserve existing account, beneficiary, ACH, history, and recurring-payment operations and their established response semantics. Sensitive values MUST not be newly exposed in logs, errors, or unrelated API responses; authorized consumers receive only the data needed for their existing operation.

#### Scenario: Existing beneficiary and ACH operation remains available
- **WHEN** a user performs an inherited beneficiary or ACH workflow using valid details
- **THEN** the workflow retains its existing API behavior while protected identifiers remain encrypted at rest
