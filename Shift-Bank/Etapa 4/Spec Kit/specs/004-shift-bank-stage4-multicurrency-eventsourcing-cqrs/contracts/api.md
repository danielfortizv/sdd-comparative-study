# Stage 4 HTTP API Contracts

This contract extends the inherited `/api` surface. Existing endpoints remain unless a stated currency/idempotency/version rule requires a compatible request extension. Monetary request fields remain protected by the existing encrypted client request envelope; TLS and AES-GCM protections remain required. Examples below show the decrypted logical payload, not a replacement for the envelope.

## Shared rules

- All money is a two-decimal string at the API boundary (`"125.40"`) and always accompanied by its currency.
- All monetary command requests require a UUID `Idempotency-Key` header and expected account versions for every affected account. Missing keys/versions are rejected before mutation.
- Accepted exact replay is checked before version validation and returns the stored original result with no new effects. Same key with a changed request fingerprint returns HTTP 409.
- Monetary command errors have no partial balance/event/projection effects. Failures are audited without including plaintext MFA or secrets.
- Limit checks precede MFA. MFA confirmation rechecks current funds, account versions, policy, and expiry under the write lock.

## `GET /api/accounts`

Returns accounts with exact currency and optimistic version:

```json
[
  {"id":"acc_checking_123","name":"Checking","balance":"5000000.00","currency":"COP","version":0},
  {"id":"CHK-1001","name":"Checking USD","balance":"2500.00","currency":"USD","version":0}
]
```

Returned balances reflect the currency-specific CQRS projection. No aggregate combines unlike currencies.

## `GET /api/accounts/{account_id}/history`

Each entry includes stable transaction/event reference, timestamp, description, direction, amount, currency, status, and optional conversion `rate`/counter-amount fields. Legacy E3 entries retain their original ID/date/direction/value and COP currency. Conversion presents a linked source debit and destination credit.

## `POST /api/transfers`

**Headers**: `Idempotency-Key: <UUID>`  
**Logical body**:

```json
{
  "source_account_id":"acc_checking_123",
  "destination_account_id":"acc_savings_456",
  "amount":"250000.00",
  "expected_versions":{"acc_checking_123":3,"acc_savings_456":7}
}
```

Only same-currency, distinct accounts are accepted. A transfer below its currency’s MFA boundary may commit immediately. A transfer requiring MFA creates `PENDING_MFA` without a debit; its confirmation is a separately idempotent monetary command.

## `POST /api/transfers/{transfer_id}/confirm-mfa`

**Headers**: a new UUID `Idempotency-Key` for the confirmation command.  
**Logical body**: six-digit `code` and `expected_versions` for all affected accounts. The code remains in the encrypted envelope, is checked in memory, and is never written to logs/audit/idempotency records in plaintext. Confirmation revalidates limits and funds; exact replay precedes version validation.

## `POST /api/transfers/ach`

**Headers**: UUID `Idempotency-Key`.  
**Logical body**: source account, amount, beneficiary ID or immutable recipient snapshot fields, `expected_versions`, and optional save-beneficiary choice. Currency policy permits COP (legacy exception) or USD; EUR/GBP is rejected. Accepted non-MFA ACH debits once and enters `PENDING`; high-value ACH uses inherited MFA before debit. Settlement does not debit again; failure refunds once.

ACH state mutations from scheduler/test-only controls use the same event/projection transaction and conditional terminal-state claim. Preserve existing test-only endpoint guards; do not make test routes public.

## `POST /api/conversions`

**Headers**: UUID `Idempotency-Key`.  
**Logical body**:

```json
{
  "source_account_id":"CHK-1001",
  "destination_account_id":"EUR-3001",
  "source_amount":"100.00",
  "expected_versions":{"CHK-1001":4,"EUR-3001":2}
}
```

Only USD/EUR/GBP pairs with different source/destination currencies are accepted. Response includes command/event references, exact source amount/currency, rational rate numerator/denominator and display rate, destination amount/currency after one HALF_UP rounding, and resulting account versions. COP and unknown pairs are rejected without effects.

## `GET /api/limits` and `PUT /api/limits`

Retain the inherited limit API surface. Include a `currency`/policy selector and report operation cap, daily cap, daily consumption, and remaining availability in either COP or USD-equivalent terms. COP policy remains 5,000,000/10,000,000 COP. USD/EUR/GBP operations use exact rational USD equivalents, with no intermediate rounding for threshold comparison. UTC daily boundary semantics remain inherited. Limit changes are audited and cannot retroactively alter completed transfers.

## Recurring and inherited endpoints

Retain beneficiary, recurring schedule, MFA, audit record/verification, health, and guarded test-only endpoints. Extend schedule/transfer responses with currency, event reference, and account version where relevant. Internal recurring source/destination currencies must match. Recurring ACH permits COP legacy and USD only. Due schedule execution uses a unique stable persisted UUID idempotency key per occurrence and applies current funds/limits. A concurrent duplicate claim for the same occurrence must resolve to the committed outcome without repeating any financial effect.

## Error contract

| HTTP | Stable code | Condition | Effects |
|---:|---|---|---|
| 400 | `INSUFFICIENT_FUNDS` | Source projection lacks requested amount. | No monetary effects; auditable rejection. |
| 400 | `LIMIT_EXCEEDED` | Operation or daily limit would be exceeded. | No debit/event; rejected before MFA. |
| 400 | `MFA_REQUIRED` / `MFA_INVALID` / `MFA_EXPIRED` | Confirmation policy or challenge failure. | No debit; existing challenge lifecycle/audit policy applies. |
| 409 | `IDEMPOTENCY_KEY_CONFLICT` | UUID key reused with a different request fingerprint. | No second command/effects. |
| 409 | `ACCOUNT_VERSION_CONFLICT` | Any expected account version is stale. | No monetary effects. |
| 409 | `TRANSFER_STATE_CONFLICT` | ACH/transfer lifecycle transition is no longer eligible. | No duplicate debit/refund. |
| 422 | `INVALID_CURRENCY` / `UNSUPPORTED_CURRENCY_PAIR` | Currency/pair is unsupported; COP conversion attempted. | No effects. |
| 422 | `INVALID_AMOUNT` / `INVALID_IDEMPOTENCY_KEY` / `MISSING_ACCOUNT_VERSION` | Malformed request, nonpositive or excess-precision amount, invalid UUID, or missing expected version. | No effects. |
| 500 | `PERSISTENCE_INTEGRITY_FAILURE` | Event/projection/audit/idempotency persistence or consistency failure. | Transaction rolls back; fail closed and audit failure when possible. |

Error response uses the existing FastAPI error envelope with a stable `detail.code` and safe `detail.message`. Never include secret material, plaintext MFA, or decrypted sensitive identifiers in an error.

## Compatibility impact

Adding mandatory `Idempotency-Key` and `expected_versions` changes old monetary request shapes. Existing React clients and encrypted payload builders must be updated in the implementation phase. Do not weaken D-13/D-14 to preserve old clients. Keep paths and response semantics otherwise backward-compatible where safe. COP-specific behavior remains explicit and separate from USD-equivalent policies.
