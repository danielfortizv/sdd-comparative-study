# Stage 4 operations and recovery

This runbook applies to the Stage 4 Spec Kit implementation. It does not authorize use against production or historical Stage 3 databases.

## Startup and configuration

The backend uses `SHIFT_BANK_DB_PATH` when set; otherwise it uses the existing application default. Configure `BANK_STORAGE_KEY`, `AUDIT_SIGNING_KEY`, `AUDIT_ADMIN_KEY`, `BANK_PRIVATE_KEY_PATH`, and `BANK_PUBLIC_KEY_PATH` through the deployment secret mechanism. The storage key must remain the same for the lifetime of ciphertext encrypted with it. Never print, commit, or rotate a storage key as a routine restart action. `/api/health` reports database connectivity, cryptographic key availability, and scheduler status.

Run only the isolated Stage 4 Compose project and a disposable named volume for acceptance checks. The inherited Compose manifest has fixed container, network, port, and volume names; verify the resolved Compose configuration and use an explicit Stage 4 override before starting containers. Do not attach an inherited or production volume.

## Migration and money safety

The Stage 4 cutover is transactional and has a migration marker. Re-running it is intended to be idempotent. It preserves existing COP account identifiers, currencies, balances, and legacy history, then provisions the four D-02 accounts additively. Before a production migration, take and verify a consistent database backup, record account IDs/currency/balance/history counts, run the migration against a copy, and compare those values after migration. Stop the application if any value or history differs; do not repair financial records manually.

Each account has one fixed currency. Internal transfers require matching currencies. USD/EUR/GBP conversion uses the approved directed rational table and exact minor-unit arithmetic. COP remains a legacy exception and has no conversion rate; never add COP to a converted dashboard total or reinterpret COP amounts as USD.

All monetary commands require a UUID `Idempotency-Key` and expected versions for affected accounts. A byte-for-byte request retry with the same key returns the stored result; reusing a key with another request is a conflict. A stale account version returns `ACCOUNT_VERSION_CONFLICT` (HTTP 409). Clients should refresh account versions and use a new key for a new user intent. Do not retry an uncertain transaction with a new key until its original outcome has been checked.

## Events, projections, and audit

Accepted monetary commands persist events, synchronous account/history projections, idempotency outcome, and HMAC audit data atomically. Domain events and the HMAC audit ledger are separate records with separate verification purposes. A rejected command must not partially change a balance, event stream, or projection.

Authorized operators can inspect `/api/projections/status` and `/api/audit/verify` with `X-Audit-Admin-Key`. Projection rebuild (`POST /api/projections/rebuild`) replays immutable events and validates reconstructed account and history state; it can update projections. Take a consistent backup and use a maintenance window before invoking it. If rebuild fails or `/api/health` is unhealthy, stop monetary writes, preserve the database and logs, and investigate the first integrity error. Do not delete events, reset a checkpoint, or bypass fail-closed checks.

## Backup and recovery

Use SQLite's online backup facility or stop the service before copying the database; copying an actively written SQLite file is not a verified backup. Back up the database and its matching key material together through the approved secret store. Protect backups as financial and sensitive data. Test restore only into a separate disposable path with the matching keys. Verify health, account balances by currency, history, projection status, and HMAC audit validity before considering a restored instance available.

Do not restore a database with different storage/HMAC keys. Do not restore Stage 3 data into Stage 4 containers without an approved migration rehearsal. A failed restore or integrity check is a stop condition, not a reason to regenerate keys or edit balances/events.

## Acceptance checks

For an isolated Stage 4 deployment, verify backend health, Nginx HTTP-to-HTTPS redirect, HTTPS static content and API routing, currency-labelled accounts, one small same-currency transfer using current versions and a fresh UUID key, account balance/history after the command, audit verification, and state after a backend restart. Use test-only generated keys and a new disposable volume. Compare conservation within each currency independently; never sum different currencies as one monetary total. Remove only the named test project resources created by that run.
