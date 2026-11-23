## Purpose

Defines the concurrency and retry contract for monetary commands so duplicate requests and stale account state cannot create repeated financial effects.

## ADDED Requirements

### Requirement: Mandatory UUID idempotency for financial requests
Internal transfer, FX conversion, and ACH requests MUST require a UUID `Idempotency-Key`. A repeated key with the identical canonical request payload MUST return the original logical result without additional financial, event, audit-success, projection, or version effects. Reuse of the same key with a different payload MUST return HTTP 409.

#### Scenario: Exact request replay
- **WHEN** a client resubmits the same operation with the same UUID key and identical canonical payload
- **THEN** the original result is returned and no additional debit, credit, financial event, or version increment occurs

#### Scenario: Key reused with a different request
- **WHEN** a UUID key already bound to one canonical payload is submitted with a different payload
- **THEN** the API returns HTTP 409 and makes no financial mutation

### Requirement: Expected account versions and validation order
Every financial command MUST include the expected version of each affected account. A stale expected version MUST return HTTP 409 with code `ACCOUNT_VERSION_CONFLICT` and MUST NOT mutate financial state. For an idempotent request, exact replay resolution MUST occur before validating expected account versions.

#### Scenario: Stale expected account version
- **WHEN** a non-replay request supplies a version different from the current version of an affected account
- **THEN** the API returns HTTP 409 `ACCOUNT_VERSION_CONFLICT` and leaves balances, events, projections, and versions unchanged

#### Scenario: Replay with now-stale version
- **WHEN** an exact idempotent replay is submitted after the account version has advanced
- **THEN** the original response is returned before version validation and no new effect occurs

#### Scenario: Concurrent commands use the same version
- **WHEN** two distinct commands concurrently submit the same expected version for an account
- **THEN** at most one commits; the other receives the version conflict and creates no financial effect
