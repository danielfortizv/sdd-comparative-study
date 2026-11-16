## Context

See `proposal.md` for motivation and `specs/` for the observable contracts. The current application is FastAPI with direct SQLite access and a React/TypeScript frontend. Stage 1 stores two COP account balances and internal transaction records; its MFA flow persists pending requests and confirms with a fixed code. The Stage 2 contract adds external recipients, shared limits, and recurring schedules while requiring restart recovery and idempotent financial effects.

## Goals / Non-Goals

**Goals:**
- Keep a single authoritative persistence boundary for balance changes, transfer state, limits, and scheduled occurrence state.
- Make all accepted monetary effects atomic, replay-safe, and recoverable after process restart.
- Reuse existing API and UI architecture where it remains suitable, while representing external recipients and recurring schedules explicitly.
- Provide a deterministic internal way to exercise ACH failure behavior without exposing an unrestricted public failure operation.

**Non-Goals:**
- Integrate with banks, ACH networks, payment providers, or real MFA services.
- Add users, authentication, multiple currencies, risk scoring, automatic limit adjustment, or configurable schedule terms beyond the approved scope.
- Change the existing MFA threshold, code, or expiration contract.

## Decisions

### 1. Extend the SQLite domain with explicit records

Keep accounts and internal transactions compatible. Add persisted user-level limit settings, beneficiaries, ACH transfer details and recipient snapshots, recurring schedules, and individual recurring occurrences. Model ACH status and recurring execution status separately so `pending`/`settled`/`failed` ACH lifecycle values do not collide with Stage 1 `PENDING_MFA`/`COMPLETED`/`EXPIRED`/`FAILED` semantics. Capture external recipient values on accepted ACH transfers and schedules rather than relying on a mutable beneficiary row. Store UTC timestamps and exact decimal strings, consistent with Stage 1.

*Alternative considered:* Put all transfer types into the existing transactions table with nullable destination account fields. This reduces table count but mixes internal ledger shape, schedule identity, and ACH lifecycle concerns. Prefer explicit ACH details and occurrence relationships while preserving the existing internal transaction representation; history can present a unified view.

### 2. Apply checks and effects in backend transactions

Centralize backend validation for positive COP amounts with at most two decimal places, available balance, strictly positive per-transfer and daily limits, and UTC daily usage. Re-run checks at the actual debit boundary: internal execution, MFA confirmation, direct ACH acceptance, and each recurring occurrence. Within one SQLite transaction, claim the stable transfer/occurrence state and apply its debit or internal credit so concurrent or repeated processing cannot create an overdraw or duplicate effect. Preserve each record's existing initiation timestamp and record the financial completion/acceptance UTC event time used to attribute daily usage: internal usage is attributed on completion, ACH usage on acceptance, and settlement does not reattribute it. Update daily usage from persisted qualifying transfer states: internal transfers count once; ACH pending and settled count once; failed ACH does not count. Limit updates are persisted for the mock user and rejected atomically when invalid. A valid reduction takes effect immediately even below current usage: accepted transactions are not reversed or rewritten, usage remains unchanged, and further transfers fail until they fit the new limit. Pending MFA operations are revalidated against current limits at confirmation.

*Alternative considered:* Rely on frontend checks or precompute and trust remaining usage at request initiation. These approaches can be stale and cannot protect concurrent requests or scheduler runs; backend transactional checks are required by the contract.

### 3. Treat MFA as authorization before acceptance

Retain the current MFA code and expiration behavior. Sensitive one-time ACH requests and recurring schedule creation remain unaccepted/inactive until confirmation. Recheck balance and current limits at one-time transfer confirmation. Before activating an MFA-protected recurring schedule, recheck that its amount is within the current per-transfer limit; evaluate shared daily usage when each occurrence is due because schedule authorization itself does not transfer funds. Only after ACH authorization and successful checks does ACH enter `pending` and debit. Successful schedule creation MFA is stored as authorization for that schedule's immutable terms; it is not a bypass for per-execution checks.

*Alternative considered:* Debit or create a pending ACH before MFA and reverse on timeout. This violates the no-debit-before-authorization invariant and adds unnecessary compensation paths.

### 4. Run persistent, restart-safe processors

Run application-owned background processing for eligible ACH settlement and due recurring occurrences, with all state persisted before acknowledging effects. ACH normal settlement becomes eligible 30 seconds after acceptance. Inject an internal settlement policy into the processor: its production default always settles normally, while automated verification can inject a deterministic outcome keyed by transfer ID to select a failure after the settlement delay. Reusing the same key after restart yields the same outcome. The policy is not exposed through a public user operation. Record simulated failures with machine-readable code `SIMULATED_SETTLEMENT_FAILURE` and the user-facing explanation "Simulated interbank settlement failed; funds were returned." The failure transition and refund occur in one idempotent database transaction, retaining the accepted transfer history and recipient snapshot.

For schedules, date-only future starts resolve to 00:00 UTC and must still be strictly in the future at creation. Without a start date, calculate the first timestamp one full interval from creation. Persist that timestamp as the cadence anchor and calculate every later occurrence from it, using exact 1-, 7-, or 30-day intervals rather than execution completion times. Display scheduled time and UTC in the interface. Define each occurrence by schedule identity and its original UTC cadence timestamp. Processing due active occurrences records a durable claim/result and applies transfer effects atomically. Resume or restart advances past missed dates without executing or counting them, but first recovers any occurrence already accepted or partially processed. An accepted recurring ACH occurrence is handed to the ACH lifecycle and is not re-executed by the scheduler.

*Alternative considered:* An in-memory timer per schedule or transfer. It would lose pending work on restart and cannot reliably prevent duplicate effects.

### 5. Keep API and presentation aligned to transfer type and lifecycle

Expose backend operations for reading/updating limits, managing beneficiaries, submitting and listing ACH transfers, and creating/listing/controlling schedules and viewing executions. Retain existing account, history, internal transfer, and MFA endpoints or compatible contracts. Frontend forms distinguish internal from ACH, validate routing number shape during entry, and present backend validation as authoritative. History renders internal and external records with appropriate statuses and recipient snapshots; account balances reflect accepted ACH debit and failed-transfer refund.

*Alternative considered:* Replace the existing transfer flow with a single opaque form and generic status. This risks breaking familiar Stage 1 behavior and obscures external recipient and lifecycle distinctions.

## Risks / Trade-offs

- **[Risk] SQLite lock contention between API requests and background processors** → Keep debit/state transitions short and atomic; claim and revalidate within the same transaction, and recover work from persisted states.
- **[Risk] The process can stop between an external effect and recording its result** → There are no external ACH effects; persist the internal simulated outcome and monetary mutation atomically, and use stable occurrence/transfer identities for replay.
- **[Risk] Existing database files may have Stage 1 rows and no Stage 2 structures** → Use additive, repeatable schema initialization and preserve seeded/existing accounts and transaction rows; do not reseed non-empty data.
- **[Risk] Time boundary or UTC-date errors can miscount daily usage and due work** → Normalize stored and compared instants to UTC and test exact UTC day boundaries and 30-second settlement boundary.
- **[Risk] Daily usage changes when an ACH transfer fails after initially counting while pending** → Derive usage from current persisted statuses and make refund/status transition atomic so failed transfers are excluded consistently.
- **[Risk] Multiple API workers could each run a processor** → Durable occurrence and lifecycle claims plus database uniqueness/state checks must make repeated or concurrent processing idempotent.

## Migration Plan

1. Add schema initialization for new tables and indexes without replacing existing account or transaction data.
2. Initialize default user limits only when no limit record exists; do not overwrite a user's configured values on subsequent startup.
3. Deploy backend operations and processors while retaining existing Stage 1 routes and response behavior.
4. Deploy frontend capabilities after compatible backend operations are available.
5. Verify an existing Stage 1 database retains balances/history and can complete existing internal transfer and MFA flows.

Rollback should stop new processors and frontend entry points first. Preserve newly created records and do not drop Stage 2 tables as part of a routine code rollback; a data rollback requires an explicit recovery decision because accepted debits and refunds are financial state.

## Open Questions

There are no unresolved business decisions. Processor polling cadence remains an implementation choice, provided it preserves the specified 30-second settlement eligibility and UTC schedule behavior.
