## Context

See `proposal.md` for scope and approved policy. The inherited SQLite schema stores account IDs and decimal text balances without a currency or account version, and it keeps mutable transaction/ACH/schedule rows. The inherited HMAC audit chain and AES-GCM data protection are separate safeguards. Stage 4 must preserve FastAPI, React/TypeScript, SQLite, Compose/Nginx/HTTPS, and observable legacy behavior while introducing currency identity, durable domain events, and rebuildable projections.

## Goals / Non-Goals

**Goals:** Specify a deterministic, auditable migration boundary; exact supported-currency operations; atomic command/event/projection/audit/idempotency persistence; and compatible read/write APIs.

**Non-Goals:** Execute or test a migration, implement application changes, add a live bank/FX service, alter the inherited audit history or keys, deploy containers, or change the approved common D-01–D-14 contracts.

## Decisions

### Monetary values and conversion

Use backend `Decimal` and frontend `BigInt` integer minor units. Keep the D-03 rates as exact numerator/denominator pairs; preserve precision through calculation and apply ROUND_HALF_UP once to the final cent amount. The API serializes all money as two-decimal strings. The one-time migration rate is a separate immutable policy value, 4,000 COP per USD; it is never exposed as an operational FX rate. For each imported balance, calculate the exact rational residual as `(source COP amount / 4000) - posted USD amount` and prove `exact converted value = posted USD + recorded residual`. The residual is not a spendable balance and cannot be plugged with a fabricated transaction. If the source/target equation cannot be proven, abort before financial mutation.

Alternative considered: binary floats or repeated per-row rounding. Both create avoidable drift and are disallowed by D-03 and the approved migration policy.

### Persisted configurable limit migration

Convert each per-user COP limit independently at the approved one-time rate of 4,000 COP per USD. Compute the exact quotient, round once to cents using ROUND_HALF_UP, then cap per-transfer and daily results at USD 5,000.00 and USD 10,000.00 respectively. Reject a rounded result below USD 0.01 rather than increasing it. Record the source value, exact quotient, rounded value, effective value, rounding residual, and any cap adjustment. The conversion belongs to the same atomic, idempotent migration batch as the account snapshot. The inherited defaults therefore become USD 1,250.00 per transfer and USD 2,500.00 daily. A repeated batch against the same snapshot is a no-op; changed source settings fail closed. Rollback must not overwrite any subsequent limit update.

### Identity and migration boundary

Keep `acc_checking` and `acc_savings` as internal foreign-key identities and expose CHK-1001/SAV-2001 as canonical public references. Accept legacy identifiers as request aliases; responses use canonical references and preserve original transaction IDs in legacy provenance. For the reported seed snapshot, initialize USD 1,250.00 and USD 3,750.00 and create zero-balance EUR-3001 and GBP-4001; disclose that these differ from common D-02 by −USD 1,250.00 and −USD 6,250.00. Do not create balancing entries.

At cutover, create one idempotent migration batch from a verified source snapshot. A migration boundary event establishes each opening projection once. Historical COP rows are imported as immutable non-posting provenance, never as additional balance effects. The event store marks the migration snapshot as genesis; initial account version is 0, and the first post-cutover financial operation advances the affected account version. All later operations use event sequence and D-09's exactly-once account-version increment.

Before any financial write, validate the approved preconditions: no pending ACH, no pending MFA for transfer/ACH/schedule, no active or paused schedule that requires migration, and zero current UTC-day transfer-limit usage. Also verify account identity/currency mappings, snapshot consistency, reconciliation, required key availability, and HMAC chain integrity. Any failed/unknown condition aborts with no financial mutation and only nonsensitive blocker identifiers. Completed/settled/failed-refunded/cancelled/expired history remains provenance. This limitation does not assert that arbitrary populated databases are migratable.

Alternative considered: replay all seeded transaction rows into snapshot balances. The code does not establish whether seed rows are already reflected in opening balances, so replay could double-post. Snapshot plus non-posting history is the approved boundary.

### Events, commands, and projections

Use the existing SQLite database as the durable event store, with append-only financial event records distinct from the inherited audit log. A single command transaction validates idempotency replay first, then expected account versions, currency/limits/balance, and any MFA authorization. It commits the complete compound event set, account projection(s), per-account version increment(s), idempotency result, and required HMAC audit outcome atomically. A rejected command does not alter balance projections or account versions; its safe rejection audit outcome is persisted when possible.

Use synchronous query projections updated in the same SQLite commit. Rebuild them deterministically from the event sequence and compare balances, currency, versions, and history. A gap, duplicate sequence, event/projection disagreement, or unverifiable migration fails closed. Keep the existing SQLite transaction serialization and single scheduler owner; scheduled occurrence identity must prevent concurrent or restart duplicates.

Alternative considered: asynchronously updated projections or a separate event database/broker. They add consistency/operational boundaries not required by D-05/D-06 and risk breaking the inherited local SQLite deployment model.

### Request identity, versions, and lifecycle

Require a UUID `Idempotency-Key` on internal transfer, conversion, and ACH requests. Canonical same-payload replay returns the stored logical result without another effect; same-key/different-payload returns 409. Replay lookup precedes expected-version validation. Each command carries expected versions for affected accounts; stale state returns 409 `ACCOUNT_VERSION_CONFLICT`. A financial command increments each affected account version once, regardless of compound event count.

An ACH acceptance debits once when it enters pending; settlement changes operation status without another debit; failure records one refund. An MFA-pending ACH has no debit before acceptance. Recurring occurrence IDs remain deterministic and unique; only active schedules run, with inherited cadence, pause/resume/cancel, and recovery semantics. D-07 limits and MFA use exact unrounded USD equivalents; D-08 currency restrictions apply before acceptance or activation.

### Audit, encryption, API, frontend, and deployment

Do not rewrite the existing HMAC chain or convert audit entries into domain events. Preserve AES-GCM ciphertext, key-version lookup, and externally provisioned keys; missing keys fail closed. New event/projection/idempotency and audit outcomes share the operation transaction. Retain existing route families, accept legacy account-ID aliases, expose canonical public references/currencies/versions, and return typed 409 errors. React uses integer cents, currency-separated totals, and clearly labelled estimate-only USD display values. Persistent SQLite storage must include event/projection/idempotency state. TLS material and runtime secrets remain external; no Compose edit or deployment is part of this specification stage.

## Risks / Trade-offs

- [D-02 deviation from fixed reference balances] → Encode the approved 1,250/3,750 values explicitly, publish both reference differences, and forbid balancing entries.
- [Legacy balances may not reflect a complete transaction ledger] → Use a verified cutover snapshot and import old records as non-posting provenance; fail if reconciliation is ambiguous.
- [Pending obligations or nonzero daily usage cannot be safely revalued] → Enforce the approved no-pending/no-schedule/no-usage precondition and leave source financial state untouched on failure.
- [SQLite event/projection/audit transaction may be unavailable or inconsistent] → Fail the command closed; prove rollback and deterministic rebuild through acceptance scenarios.
- [Legacy account IDs and canonical public references differ] → Keep stable internal keys, test both request aliases, and expose unambiguous canonical response identifiers.
- [External TLS/configuration paths differ from current local Compose references] → Keep deployment specifications explicit about external provisioning; make no deployment claim until a separately authorized configuration adaptation is verified.

## Migration Plan

The migration is a future implementation operation and is not executed in this change. The specified sequence is: stop financial writes; acquire and identify a consistent SQLite snapshot; verify audit-chain/key availability and approved preconditions; validate account identity and COP semantics; calculate exact account and per-user limit conversions and residuals; write the idempotent snapshot/genesis events, canonical mapping, non-posting history provenance, converted limit settings, projections, and audit outcome atomically; reconcile source and target; then enable Stage 4 commands. A failed precommit step leaves the source state unchanged. A repeated identical batch is a no-op. Recovery after committed post-cutover events or subsequent limit edits must preserve those events and settings and refuse any rollback that would lose, overwrite, or double-apply effects; unresolved recovery remains fail-closed for researcher/operator review.

## Open Questions

- Runtime-specific external secret/configuration binding and operational backup details are deferred to a separately approved implementation/deployment plan and cannot weaken these requirements.
