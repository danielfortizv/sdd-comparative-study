# Stage 4 Domain Event Contract

The domain event stream is the authoritative post-cutover record of monetary state transitions. It is append-only and distinct from the inherited HMAC audit chain. Audit records provide tamper evidence and security/operational attribution; domain events provide deterministic monetary reconstruction.

## Event envelope

Every event carries `event_id`, committed `sequence`, `event_type` and schema version, `command_id`, UTC `occurred_at`, `account_ids`, fixed per-account currency, event payload, and optional source/idempotency correlation. Financial values are exact minor-unit integers or canonical two-decimal text. FX/risk comparisons retain rational numerator/denominator. Payloads must omit plaintext MFA, secrets, keys, and unnecessary sensitive fields.

## Event catalog

| Event | Balance effect | Version effect | Purpose |
|---|---|---|---|
| `AccountOpeningBalanceSnapshot` | Establishes inherited account cutover projection exactly once. | Sets baseline version 0. | Reconstruct current E3 balance without replaying old transfer deltas. |
| `LegacyHistoryImported` | None. | None. | Preserves an E3 history row for display/replay without double counting. |
| `ReferenceAccountProvisioned` | Establishes a missing D-02 account’s specified opening value. | Sets baseline version 0. | Idempotent initial D-02 provisioning. |
| `InternalTransferCompleted` | Composite source debit and same-currency destination credit. | Each of the two accounts increments once. | Accepted immediate transfer. |
| `InternalTransferMfaPending` / `InternalTransferMfaResolved` | Pending event has no debit; resolved success creates one monetary transfer event. | No balance version on pending; one increment on success per affected account. | Preserve inherited MFA lifecycle. |
| `CurrencyConversionCompleted` | Composite debit/credit across supported different non-COP currencies. | Each account increments once. | Stores source/destination values and applied rational rate. |
| `AchTransferAccepted` | One source debit when accepted (after MFA if required). | Source increments once. | Creates pending ACH and immutable recipient snapshot. |
| `AchTransferSettled` | None. | No account version increment. | Status-only transition; no second debit. |
| `AchTransferFailed` | None by itself. | No increment unless a refund is applied in the same atomic command. | Terminal failure status. |
| `AchTransferRefunded` | One source credit. | Source increments once. | Exactly-once refund, conditional on pending/nonterminal status. |
| `RecurringScheduleCreated/Authorized/Paused/Resumed/Cancelled` | None. | No balance version increment. | Schedule lifecycle state. |
| `RecurringExecutionCompleted` | One internal same-currency transfer or one supported ACH debit. | Each changed internal account increments once; ACH source once. | One scheduled occurrence with stable idempotency key. |
| `RecurringExecutionFailed` | None. | No balance version increment. | Failure and due-date advancement per inherited behavior. |

Each status lifecycle event is idempotent by event/source identity. A failure or settlement event cannot apply a debit/refund twice. A recurring occurrence has one unique persisted idempotency identity; concurrent workers for that occurrence serialize through the command transaction, and a retry returns the committed outcome without appending another monetary event group.

## Atomicity and idempotency

For one accepted command, append the required event group; update all affected account/history/operational projections; append the legacy audit entry; store the idempotency outcome; and commit in one SQLite write transaction. A failure before commit leaves none of these accepted-command effects. Rejections and security failures use the inherited separate atomic audit path without monetary changes.

Request handling resolves an already accepted identical idempotency key/fingerprint first, before checking current account versions. It returns the original response without appending any event or audit success record. A reused key with another fingerprint is HTTP 409. New commands then check every expected account version and perform currency, limit, balance, and MFA validation under the write lock.

## Projection replay

1. Apply `AccountOpeningBalanceSnapshot` / `ReferenceAccountProvisioned` as version-zero state.
2. Apply `LegacyHistoryImported` to history only.
3. Apply later events in committed sequence; reject duplicate event IDs and invalid per-account version transitions.
4. Validate account currency immutability, amount positivity/precision, transfer conservation, FX rate/result consistency, ACH exactly-once debit/refund, and recurring state transitions.
5. Produce the same currency-labelled account/history/operational projections on every replay. Any failed invariant prevents activation of that projection and requires an auditable integrity error; never skip/repair events silently.

## Audit relationship

Domain events and HMAC audit entries are written atomically for accepted financial operations but remain distinct records with distinct purposes and APIs. Audit entries contain safe event/command references and digests, not sensitive payloads. Existing audit verification/checkpoint semantics remain; event replay is not a replacement for audit verification, and audit verification is not a balance-rebuild mechanism.
