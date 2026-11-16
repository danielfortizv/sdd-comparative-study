# Research and Decisions: Shift Bank Stage 4

**Feature**: `004-shift-bank-stage4-multicurrency-eventsourcing-cqrs`  
**Decision authority**: researcher-delegated technical-supervisor resolution, 2026-11-16  
**Research mode**: local E4 Spec Kit baseline and inherited Spec Kit sources only; no external service or Tessl source used.

## Decision 1 — Preserve COP and add reference accounts

**Decision**: Keep E3 accounts `acc_checking_123` / `acc_savings_456`, COP 5,000,000.00 / COP 15,000,000.00, and all legacy transaction history. Add all four D-02 accounts at their exact listed currencies and initial values. Provisioning is insert-if-absent and validates existing identities; it never resets a balance.

**Rationale**: The seed prohibits silent monetary value changes. No COP/USD conversion rate is approved. The delegated contract explicitly authorizes additive accounts and preserves COP as a legacy exception.

**Alternatives considered**: Replace/relabel the COP accounts with USD (rejected: changes currency/value and IDs); preserve COP only and omit D-02 accounts (rejected: violates the delegated contract); keep COP plus reference accounts (selected).

## Decision 2 — Cutover snapshot and legacy history

**Decision**: At migration cutover, represent each current inherited balance with one `AccountOpeningBalanceSnapshot` event. Represent each old history row as a `LegacyHistoryImported` event with no monetary balance effect. New post-cutover money movements are represented by monetary domain events and applied to projections once. Use a unique migration marker and source-row/event IDs to make re-entry idempotent.

**Rationale**: E3 accounts contain current balances and separate transaction rows; replaying the history as new movements on top of the current balance could double count. This strategy preserves both current value and customer-visible history without inventing an E3 opening-ledger reconstruction.

**Alternatives considered**: Recompute current balance solely from transaction history (rejected: no complete opening ledger is guaranteed); replay historical transfers as monetary deltas atop current balances (rejected: double count); snapshot balances and import history without monetary effects (selected).

## Decision 3 — Currency-specific policies

**Decision**: Keep fixed currency per account. COP stays outside FX, retains COP 5,000,000 per-operation / COP 10,000,000 daily caps and MFA at `>= COP 1,000,000`. USD/EUR/GBP use D-07 exact unrounded USD-equivalent limits and MFA strictly above USD 1,000. The fixed EUR→USD (10/9) and GBP→USD (10/8) rational rates determine non-USD comparisons; equality is allowed for limits and does not trigger MFA at exactly USD 1,000.

**Rationale**: This implements the reference semantics without adding an unapproved COP rate or reinterpreting peso amounts.

**Alternatives considered**: Convert COP to USD (rejected: no rate); apply D-07 USD figures directly to all currencies (rejected: wrong currency units); preserve COP policy and apply exact rational USD equivalents only to USD/EUR/GBP (selected).

## Decision 4 — Fixed FX policy and rounding

**Decision**: Use only the six directed rational USD/EUR/GBP rates in `02_D01_D14_REFERENCE.md`. Persist numerator/denominator and the final source/destination values. Convert exactly and round destination minor units once using `ROUND_HALF_UP`. Charge no fees. Reject COP and unsupported pairs.

**Rationale**: Rates and sanity checks are explicitly provided; a live or variable rate source would add scope and destroy deterministic comparisons.

## Decision 5 — Event and projection architecture

**Decision**: Keep a modular monolith and existing SQLite. Store append-only monetary domain events separately from HMAC audit records. Update event rows, account/history projections, audit, and accepted idempotency outcomes in one SQLite write transaction. Rebuild projections deterministically from the snapshot/import events and subsequent events; fail closed on inconsistent ordering, currency, version, or conservation.

**Rationale**: D-05/D-06/D-11 require durable events distinct from audit, atomic synchronous projections, deterministic rebuild, and failure atomicity. A message broker or separate service is unnecessary for the single-user local application and is not authorized.

**Alternatives considered**: Treat audit rows as domain events (rejected); add a broker or external event-store service (rejected by scope/proportionality); use SQLite event rows and projections in the existing application transaction boundary (selected).

## Decision 6 — Idempotency and concurrency

**Decision**: Require UUID `Idempotency-Key` for transfers, FX, ACH, and monetary confirmation commands. Canonicalize and fingerprint accepted request semantics without storing plaintext MFA or sensitive fields. On accepted replay with the same payload, return the stored result before validating account versions; changed payload for the same key returns HTTP 409. Require expected versions for all affected accounts; reject stale commands with HTTP 409 `ACCOUNT_VERSION_CONFLICT`. Increment each changed account version once per accepted monetary command.

**Rationale**: Directly implements D-13/D-14 and prevents duplicate effects under retries and concurrent requests.

## Decision 7 — Preserve ACH/recurring and security behavior

**Decision**: Allow COP ACH/recurring ACH as explicit legacy exceptions and USD ACH/recurring ACH under D-08; reject EUR/GBP ACH. Same-currency internal recurring remains supported. Preserve immediate ACH debit, no second debit at settlement, exactly one failure refund, existing schedule state machine, AES-GCM, HMAC audit, encrypted client-originated sensitive payloads, external key configuration, and HTTPS deployment support.

## Inherited source observations used in design

- E3 seed/schema and COP default policy are present in `backend/src/database.py` and E3 Stage 1–3 specifications.
- Existing REST surfaces cover accounts/history, transfers/MFA, ACH, limits, recurring schedules, audit, and health. Exact E3 contracts are documented in `specs/001-shift-bank-stage1/contracts/api.md` and `specs/002-shift-bank-stage2/contracts/api.md`.
- Stage 3 adds AES-GCM protected requests/storage, HMAC audit, Locust load testing, and Compose/Nginx/TLS deployment. Stage 4 adds separate monetary domain events and projections; it must not conflate the existing audit chain with the new event stream.
- The E4 baseline intentionally excludes E3 database files. This design specifies future migration behavior but does not claim to have inspected or migrated a runtime database.

## Provenance limitations

The operative full `SEED-4.md` packet copy is unchanged and its declared hash is recorded in the specification. The original standalone seed master and full original D-01–D-14 approval documents were not found in accessible E4 materials. The 2026-11-16 researcher message delegated decision-making and explicitly supplied the complete prospective compatibility contract; this message, not a recovered historical approval file, is the source for the COP exceptions in this Stage 4 specification. No Tessl implementation, tests, or specifications informed these decisions.

## Open implementation-time verification (not business blockers)

- Confirm exact E3 schema/data variants against a safely isolated copy of the intended database before authoring migration code; the E4 baseline contains no E3 database file.
- Confirm event payload serialization and SQLite indexes during implementation design without changing event semantics or the accepted contract.
- Execute only on isolated disposable data after Gate B; no tests, migration, container, load, or deployment operation was run for this research artifact.
