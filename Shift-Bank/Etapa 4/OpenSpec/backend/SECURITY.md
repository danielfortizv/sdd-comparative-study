# Sensitive banking data key provisioning

The API does not generate or persist encryption keys. Provision a JSON keyring externally through `SHIFT_BANK_ENCRYPTION_KEYS` or mount that JSON as a secret file and set `SHIFT_BANK_ENCRYPTION_KEYS_FILE`. Set `SHIFT_BANK_ACTIVE_KEY_VERSION` to the key version used for new records.

Each JSON entry maps a version label to a standard Base64 encoded 32-byte key. Generate a fresh value in a secure environment, for example:

```sh
python -c "import base64,secrets; print(base64.b64encode(secrets.token_bytes(32)).decode())"
```

Do not put generated values in source control, SQLite, logs, tickets, or test evidence. Supply keys through the deployment's protected secret mechanism. File permissions and backup custody are the operator's responsibility.

For rotation, add the new key version while retaining every prior version required to decrypt stored rows, then set `SHIFT_BANK_ACTIVE_KEY_VERSION` to the new version. The application writes new ciphertext with the active key and continues to read old ciphertext with its recorded version. Remove an old key only after all rows using it have been deliberately re-encrypted and verified. Missing key versions fail closed; the application does not try plaintext or another key.

The encrypted field format is `sbenc:v1:<key-version>:<base64url(nonce || ciphertext-and-tag)>`. AES-256-GCM uses a random 96-bit nonce and authenticates the table, record identifier, field name, and format version. Authorized API operations decrypt values in memory and retain their inherited response shape. Sensitive routes and responses require HTTPS; reverse proxies may assert HTTPS only when their source IP is listed in `SHIFT_BANK_TRUSTED_PROXY_IPS`.

## Transactional audit key and verification access

Provision a separate 32-byte key as standard Base64 in `SHIFT_BANK_AUDIT_KEY`; do not reuse a data-encryption key. Set `SHIFT_BANK_AUDIT_ADMIN_TOKEN` to a separately provisioned high-entropy token for the HTTPS-only `GET /api/admin/audit/verify` endpoint, using `Authorization: Bearer <token>`. The verification response contains validity, checked sequence range, and a safe failure position/reason; it never returns the audit key. There is no application endpoint to reset or delete the audit chain.

Audit records are HMAC-SHA-256 chained in canonical sequence order. SQLite triggers reject application-level updates/deletes, and a keyed checkpoint detects database-only row or head edits while the checkpoint remains present. Successful banking mutations and their audit events commit in the same SQLite transaction. The chain does not guarantee detection if an operator can rewrite both the complete database and the application/secret environment; the approved threat model excludes an operator controlling the database, application, and all cryptographic secrets.
