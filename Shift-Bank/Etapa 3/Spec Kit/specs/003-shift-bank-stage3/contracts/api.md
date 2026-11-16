# API Contracts: Shift Bank Stage 3 — Security Hardening, Audit Integrity, and Deployment

This document specifies the REST API contracts, cryptographic envelope schemas, audit verification endpoints, and deployment health endpoints for Shift Bank Stage 3, extending the Stage 2 API surface while preserving brownfield compatibility.

---

## 1. Cryptographic Envelope Schema (Client-to-Server Requests)

All sensitive client-originated requests (`POST /api/transfers`, `POST /api/transfers/{id}/confirm-mfa`, `POST /api/ach/transfers`, `POST /api/beneficiaries`, `POST /api/recurring-transfers`, `PUT /api/limits`) must transmit payloads wrapped in an authenticated `CryptographicEnvelope`.

### Schema: `CryptographicEnvelope`
```json
{
  "type": "object",
  "required": ["encrypted_key", "iv", "ciphertext", "tag"],
  "properties": {
    "encrypted_key": {
      "type": "string",
      "description": "Base64-encoded ephemeral AES-256 key encrypted using backend's RSA-OAEP public key."
    },
    "iv": {
      "type": "string",
      "description": "Base64-encoded 12-byte initialization vector generated per request."
    },
    "ciphertext": {
      "type": "string",
      "description": "Base64-encoded AES-256-GCM ciphertext of the JSON serialized request model."
    },
    "tag": {
      "type": "string",
      "description": "Base64-encoded 16-byte AES-GCM authentication tag."
    }
  }
}
```

### Decryption Error Schema (HTTP 400 Bad Request / 422 Unprocessable Entity)
When an envelope cannot be unwrapped, deciphered, or authenticated:
```json
{
  "detail": "Invalid cryptographic envelope: decryption or tag verification failed."
}
```

---

## 2. Cryptographic Key Management Endpoints

### `GET /api/crypto/public-key`
Retrieves the active RSA public key in PEM format used by clients to wrap ephemeral AES keys.

- **Authentication**: Unauthenticated (public).
- **Responses**:
  - **`200 OK`**:
    ```json
    {
      "algorithm": "RSA-OAEP-256",
      "format": "PEM",
      "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n-----END PUBLIC KEY-----\n",
      "key_id": "bank_pub_v1"
    }
    ```

---

## 3. Encrypted Banking Endpoints

### `POST /api/transfers`
Initiates an internal transfer between user accounts. Sensitive fields (`source_account_id`, `destination_account_id`, `amount`) are wrapped in `CryptographicEnvelope`.

- **Headers**: `Content-Type: application/json`
- **Request Body**: `CryptographicEnvelope` wrapping `TransferCreate`:
  ```json
  {
    "source_account_id": "acc_checking",
    "destination_account_id": "acc_savings",
    "amount": "150000.00"
  }
  ```
- **Responses**:
  - **`200 OK` (Standard transfer completed)**:
    ```json
    {
      "id": "tr_123e4567-e89b-12d3-a456-426614174000",
      "source_account_id": "acc_checking",
      "destination_account_id": "acc_savings",
      "amount": "150000.00",
      "status": "COMPLETED",
      "transfer_type": "INTERNAL",
      "created_at": "2026-11-15T20:00:00.000000Z"
    }
    ```
  - **`202 Accepted` (Sensitive transfer requiring MFA, $\ge \text{COP } 1,000,000.00$)**:
    ```json
    {
      "id": "tr_123e4567-e89b-12d3-a456-426614174001",
      "source_account_id": "acc_checking",
      "destination_account_id": "acc_savings",
      "amount": "1500000.00",
      "status": "PENDING_MFA",
      "transfer_type": "INTERNAL",
      "created_at": "2026-11-15T20:00:00.000000Z",
      "expires_at": "2026-11-15T20:05:00.000000Z",
      "mfa_required": true,
      "message": "Transfer requires step-up MFA authorization."
    }
    ```
  - **`400 Bad Request`**: Limit exceeded, insufficient funds, or corrupted ciphertext.

---

### `POST /api/transfers/{id}/confirm-mfa`
Validates step-up authentication PIN for a pending transfer.

- **Request Body**: `CryptographicEnvelope` wrapping:
  ```json
  {
    "mfa_code": "123456"
  }
  ```
- **Responses**:
  - **`200 OK`**: Transfer completed successfully.
  - **`400 Bad Request`**: Invalid PIN or expired transfer.

---

### `POST /api/ach/transfers`
Initiates an external third-party ACH transfer.

- **Request Body**: `CryptographicEnvelope` wrapping `AchTransferCreate`:
  ```json
  {
    "source_account_id": "acc_checking",
    "recipient_name": "Maria Morales",
    "bank_name": "Banco de Bogota",
    "routing_number": "123456789",
    "account_number": "9876543210",
    "amount": "250000.00"
  }
  ```
- **Responses**:
  - **`200 OK`**: ACH transfer queued (`status: "PENDING"`).
  - **`202 Accepted`**: ACH transfer pending MFA ($\ge \text{COP } 1,000,000.00$).

---

### `POST /api/beneficiaries`
Creates a saved ACH beneficiary.

- **Request Body**: `CryptographicEnvelope` wrapping `BeneficiaryCreate`:
  ```json
  {
    "name": "Maria Morales",
    "bank_name": "Banco de Bogota",
    "routing_number": "123456789",
    "account_number": "9876543210"
  }
  ```
- **Responses**:
  - **`201 Created`**: Beneficiary created with encrypted persistence at rest.

---

### `POST /api/recurring-transfers`
Creates an automated recurring transfer instruction.

- **Request Body**: `CryptographicEnvelope` wrapping `RecurringScheduleCreate`.
- **Responses**:
  - **`201 Created` / `202 Accepted`**: Schedule created (`ACTIVE` or `PENDING_MFA`).

---

## 4. Audit Trail & Verification Endpoints (E3-AUD-01)

### `GET /api/audit/verify`
Traverses the append-only audit trail and mathematically validates sequence continuity, cryptographic HMAC links, and payload digests.

- **Headers**:
  - `X-Audit-Admin-Key: <ADMIN_SECRET>` (Mandatory)
- **Query Parameters**:
  - `expected_head_hash` (string, optional): External trusted checkpoint head HMAC to detect tail truncation.
  - `expected_count` (integer, optional): Expected minimum record sequence number.
- **Responses**:
  - **`200 OK` (Verification Succeeded)**:
    ```json
    {
      "is_valid": true,
      "verified_records": 42,
      "latest_sequence": 42,
      "latest_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "details": "Audit chain verified intact from genesis to head.",
      "broken_sequence": null,
      "tail_truncation_detected": false
    }
    ```
  - **`200 OK` (Tampering or Truncation Detected)**:
    ```json
    {
      "is_valid": false,
      "verified_records": 15,
      "latest_sequence": 15,
      "latest_hash": "a1b2c3...",
      "details": "Integrity violation: Hash mismatch detected at sequence 16.",
      "broken_sequence": 16,
      "tail_truncation_detected": false
    }
    ```
  - **`401 Unauthorized` / `403 Forbidden`**:
    Missing or invalid `X-Audit-Admin-Key` header.
    ```json
    {
      "detail": "Unauthorized: Administrative verification key required."
    }
    ```

---

### `GET /api/audit/records`
Retrieves paginated non-sensitive audit metadata.

- **Headers**: `X-Audit-Admin-Key: <ADMIN_SECRET>`
- **Query Parameters**: `limit` (default 50), `offset` (default 0).
- **Responses**:
  - **`200 OK`**:
    ```json
    [
      {
        "id": 1,
        "timestamp": "2026-11-15T20:00:00.000000Z",
        "event_type": "TRANSFER_COMPLETED",
        "actor_id": "user_mock_001",
        "resource_id": "tr_123e4567-e89b-12d3-a456-426614174000",
        "payload_digest": "4a5b6c...",
        "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
        "record_hmac": "e3b0c4..."
      }
    ]
    ```

---

## 5. Deployment Health Endpoint (E3-DEP-01)

### `GET /api/health`
Used by Docker healthchecks, Nginx reverse proxy monitoring, and automated deployment smoke tests.

- **Authentication**: Unauthenticated.
- **Responses**:
  - **`200 OK`**:
    ```json
    {
      "status": "healthy",
      "database": "connected",
      "scheduler_active": true,
      "crypto_keys_loaded": true,
      "environment": "production"
    }
    ```
  - **`503 Service Unavailable`**:
    Database unreachable or cryptographic keys missing/invalid.
    ```json
    {
      "status": "unhealthy",
      "database": "error",
      "details": "Database connection failed or keys unreadable."
    }
    ```
