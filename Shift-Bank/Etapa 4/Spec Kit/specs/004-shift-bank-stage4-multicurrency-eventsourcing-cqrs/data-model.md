# Stage 4 Data Model

This is a logical design constrained by the approved contract. Physical schema changes are future implementation work and require Gate B.

## Entities

### Account

| Field | Meaning / constraint |
|---|---|
| `account_id` | Stable identifier. Preserve E3 IDs exactly; add the four D-02 IDs exactly. Unique. |
| `user_id` | Existing mock customer owner; retain established scope. |
| `name` / `type` | Existing friendly label and checking/savings type; reference account names follow the D-02 role. |
| `currency` | Required immutable ISO code: inherited COP or USD/EUR/GBP. No heterogeneous balance. |
| `balance_minor` | Exact integer minor units in the currency's two-decimal representation; derived projection. |
| `version` | Nonnegative optimistic concurrency token. Starts at 0 for the cutover/provisioned snapshot; increments once for each later accepted monetary command affecting the account. |
| `created_at` / `status` | Preserve existing values where present; status must permit existing account workflows. |
| `provisioning_source` | Optional provenance marker (`E3_CUTOVER` or `D02_REFERENCE`); never changes financial value. |

**Invariants**: currency is immutable; balance is never interpreted in another currency; the account version equals the last applied monetary command version; projection can be rebuilt.

### Domain Event

| Field | Meaning / constraint |
|---|---|
| `event_id` | Globally unique immutable identifier; duplicate application is rejected/ignored only by exact event identity. |
| `sequence` | Deterministic committed order for replay. |
| `event_type` | Versioned event name from `contracts/events.md`. |
| `command_id` | Groups the composite effects of one accepted command. |
| `account_id` / `currency` | Affected aggregate identity and fixed currency; multi-account events carry an ordered account set. |
| `account_version` | Version after the command for each changed account; one increment per affected account per command. Snapshot/import events establish version zero. |
| `amount_minor` | Exact source or destination amount where applicable; no floats. |
| `rate_numerator` / `rate_denominator` | Required for conversion and non-COP USD-equivalent limit decisions; exact directed rational. |
| `occurred_at` | UTC operation timestamp, distinct from event persistence ordering. |
| `payload` | Minimal validated event data; never plaintext MFA, secrets, raw private keys, or unnecessary sensitive identifiers. |
| `source_reference` | Legacy transfer/migration source ID or idempotency key reference; unique where used for import. |

Events are append-only. Corrections are compensating events; update/delete is prohibited by application policy and storage protections.

### Legacy History Import

`LegacyHistoryImported` records one preserved E3 history entry with exact ID, date, direction, amount, currency, and description. It populates history projection only and has no balance effect. A legacy reference uniqueness key prevents duplicate imports.

### Account Balance / History Projections

- **Account projection**: current exact balance, immutable currency, version, status, and migration provenance keyed by account ID.
- **History projection**: one entry per legacy import or post-cutover transaction movement, with explicit currency and event/transaction references. FX creates linked debit and credit entries with source/destination values and the applied rate.
- **Operational projection**: ACH status/refund and recurring schedule state used by existing queries/workers. It is rebuilt or reconciled from domain events and retains immutable beneficiary snapshots.

All projections are derived data. They update in the same transaction as their source event(s).

### Idempotency Record

| Field | Constraint |
|---|---|
| `key` | Required UUID `Idempotency-Key`; unique in the command namespace. |
| `command_type` | Transfer, conversion, ACH, confirmation, or scheduled monetary execution. |
| `request_fingerprint` | Canonical payload digest; does not retain plaintext MFA or raw secret data. |
| `outcome` | Stored successful response/event references for exact replay. |
| `created_at` | UTC. |

Same key + same accepted request returns the stored result without new effects. Same key + changed payload returns HTTP 409. The result is committed atomically with the accepted command.

### Audit Record

Retain the existing monotonically sequenced HMAC-chained audit entity. It remains separate from domain events. Financial event payloads must not leak MFA PINs, secrets, or raw sensitive values. Successful operations and audit rows are atomic; rejected/security failures follow the existing separate auditable failure path.

### Limit Policy

| Policy | Operation limit | Daily limit | MFA boundary |
|---|---:|---:|---|
| COP legacy | COP 5,000,000.00 | COP 10,000,000.00 | `amount >= COP 1,000,000.00` |
| USD | USD 5,000.00 equivalent | USD 10,000.00 equivalent | unrounded USD equivalent `> USD 1,000.00` |
| EUR | USD 5,000.00 equivalent | USD 10,000.00 equivalent | unrounded EUR→USD equivalent `> USD 1,000.00` |
| GBP | USD 5,000.00 equivalent | USD 10,000.00 equivalent | unrounded GBP→USD equivalent `> USD 1,000.00` |

Daily reset remains UTC as inherited. USD equivalence for EUR/GBP uses fixed rationals and no intermediate rounding; exact limit equality is allowed. A rate is not applied to COP.

### Conversion Rate

An immutable directed-pair record: source currency, destination currency, numerator, denominator, rate version, and effective time. For this stage, rates are fixed to the supplied table: USD→EUR 9/10; USD→GBP 8/10; EUR→USD 10/9; GBP→USD 10/8; EUR→GBP 8/9; GBP→EUR 9/8. No fees or COP pair exist.

### ACH and Recurring Schedule

Retain existing attributes, lifecycle, and recipient snapshot. Add/require fixed source currency, expected account version at customer command boundaries, event references, and idempotency references. ACH permits COP legacy and USD; rejects EUR/GBP. Internal recurring endpoints require same-currency accounts. Recurring ACH permits COP legacy and USD only.

## Relationships

- One mock user owns accounts.
- One command produces one or more immutable events.
- A transfer affects two same-currency accounts; a conversion affects two non-COP accounts of different supported currencies.
- An ACH transfer affects one source account and an external recipient snapshot.
- Account and history projections are derived from cutover/provision events plus later events; legacy history import events never change balances.
- An idempotency record maps one UUID command key to its request fingerprint and committed outcome.
- Audit records reference command/event IDs by opaque correlation identifier, not by embedding sensitive event payloads.

## State and Version Rules

- **Internal transfer**: accepted command creates a composite event; source debit and destination credit share command ID; each account version advances once.
- **Conversion**: composite debit/credit records source and destination amounts/rate; both account versions advance once.
- **MFA pending**: challenge/transfer status may be recorded but does not debit funds or increment account balance versions. Confirmation revalidates versions, limits, funds, and MFA before committing the monetary command.
- **ACH**: accepted standard ACH debits source once and enters `PENDING`; settlement changes status only; failure applies one refund event/credit and becomes terminal.
- **Recurring**: schedule lifecycle and each execution are events. An execution uses a stable persisted UUID command key; failed balance/limit execution records failure and advances due date per inherited contract without a debit.
- **Concurrency**: command checks all expected versions under the SQLite write transaction. Stale commands return HTTP 409 `ACCOUNT_VERSION_CONFLICT` and do not append monetary events.

## Migration and Rollback Invariants

1. Read the E3 source state from an isolated intended database copy only after Gate B.
2. Preserve account IDs, COP currency, exact encrypted monetary value after decrypting through authorized application code, histories, pending MFA/ACH/recurring state, limits, beneficiaries, and HMAC audit records.
3. Write one cutover opening snapshot per account at version 0, plus no-balance-effect history import events for each inherited transaction.
4. Provision D-02 accounts only if their IDs are absent. If an ID exists with incompatible attributes/value, abort; do not overwrite.
5. Mark the migration source/version and imported source IDs so retries cannot duplicate events.
6. Commit schema, events, projections, migration marker, and any audit transition atomically; on any validation/persistence failure, roll back to an E3-usable database and retain an independently protected pre-migration recovery copy according to deployment operations review.
7. Verify projected opening balances and history exactly before serving Stage 4 queries. No automatic “repair” or conversion is allowed.
