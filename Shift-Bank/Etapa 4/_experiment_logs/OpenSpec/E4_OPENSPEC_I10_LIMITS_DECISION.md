# Iteration 10 — Legacy transfer-limit migration decision

## Status

Analysis only. The proposed policy below is a recommendation, not researcher approval. No OpenSpec specification was changed, no database was opened, no test was rerun, and no financial state was modified. Approval is required before the affected Stage 4 contracts can be finalized.

## Inherited behavior and evidence

- The SQLite schema defines transfer_limits(user_id TEXT PRIMARY KEY, per_transfer TEXT NOT NULL, daily TEXT NOT NULL, updated_at TEXT NOT NULL) in backend/database.py:41-43. Values are user-specific, not global. The application currently has one mock user, usr_101 (backend/banking.py:15); transfers share that user's limits across accounts and internal, ACH, and recurring activity.
- When a user row is absent, initialization inserts per_transfer=5,000,000.00 and daily=10,000,000.00 with a timestamp (backend/database.py:82-83). The approved Stage 2 transfer-limits spec labels both defaults COP (openspec/changes/stage2-banking-enhancements/specs/transfer-limits/spec.md).
- GET /api/limits returns saved values and current daily usage; PUT /api/limits updates both values (backend/main.py:159-166). save_limits uses the inherited positive-amount/two-decimal validation, writes both fields transactionally, appends a transfer_limits_changed audit event, and returns the new limits (backend/banking.py:48-62, 224-232). The inherited update path has no D-07 maximum.
- test_banking.py verifies saved settings survive database initialization (47-56), invalid zero/negative/malformed/over-precision settings are rejected without changing the prior value, and a lowered daily setting applies immediately (80-89). It also tests exact per-transfer boundaries and current-limit revalidation (91-117, 205-215, 266-305). The API test verifies the initial default per-transfer value (test_api.py:109-110). These tests were inspected, not rerun.
- An operation is checked against the configured per_transfer amount; accumulated daily usage is the sum of completed internal transactions by completion/timestamp plus pending or settled ACH by accepted_at within UTC midnight bounds (banking.py:110-118, 132-145). Failed/refunded ACH is excluded by status. Recurring execution and MFA confirmation revalidate current limits. Daily use is shared, not counted per account debit/credit.
- The inherited spec makes limit updates immediately effective, retains a positive per-transfer and UTC daily limit, and defines exact equality as allowed. Its currency is COP. The Stage 4 D-07 contract defines USD-equivalent ceilings of USD 5,000 per operation and USD 10,000 daily; Stage 4 limit configuration must stay within those ceilings and operate on exact USD equivalents.
- No real or runtime SQLite database was opened. The copied source inventory had no persisted DB file; the current actual saved per-user settings are therefore NOT VERIFIED.

## Alternatives

| Alternative | Effect | Compatibility and risk |
|---|---|---|
| A. Convert saved COP limits at 4,000 COP/USD | Convert each saved per_transfer and daily value using the already approved one-time rate, retain user-specific lower settings, and constrain each result to its D-07 ceiling. Seed defaults become USD 1,250.00 per transfer and USD 2,500.00 daily. | Best preserves the inherited user's selected restriction and dynamic update behavior. It is deterministic and does not reset limits upward. It intentionally makes effective limits lower than the D-07 ceilings. |
| B. Reset all saved values to D-07 defaults | Set per_transfer to USD 5,000.00 and daily to USD 10,000.00 regardless of legacy settings. | Simple, but discards customized settings and loosens inherited defaults by four times under the approved rate. It can increase permitted exposure and conflicts with preserving inherited configuration. |
| C. Reject non-default legacy configurations | Migrate only when saved values equal the known inherited defaults; abort for any customized values pending individual reconciliation. Default values still require an explicit conversion rule. | Strong fail-closed handling for unknown custom settings, but prevents migration for users who intentionally set tighter limits and does not define default mapping by itself. It preserves safety at the cost of availability and reproducibility for customized records. |

## Recommendation: Alternative A, for explicit approval

For each user row, use exact rational arithmetic:

- exactConvertedUSD = savedCOP / 4000
- roundedUSD = exactConvertedUSD rounded once to cents with ROUND_HALF_UP
- effectiveUSD = min(roundedUSD, applicable D-07 ceiling)

Keep the source COP value, exact rate, rounded result, any rounding residual, and any ceiling reduction in migration provenance/audit evidence. Do not silently raise a rounded result to the minimum. The minimum effective configured value is USD 0.01, consistent with inherited positive two-decimal validation. If a positive COP setting rounds below USD 0.01, abort migration before financial mutation and identify the setting by nonsensitive user/field identifiers. If a converted value exceeds a D-07 ceiling, clamp down to the ceiling and record the exact pre-cap result and cap reduction; never exceed USD 5,000 per operation or USD 10,000 daily. Preserve per-transfer and daily values independently; the inherited system permits daily limits below per-transfer limits.

For inherited defaults, the exact results are:
- COP 5,000,000.00 / 4,000 = USD 1,250.00 per transfer.
- COP 10,000,000.00 / 4,000 = USD 2,500.00 daily.

These are each one quarter of their respective D-07 ceilings. The conversion changes neither balances nor daily usage; the already approved migration precondition requires current-day usage to be zero. It preserves a configured restriction instead of resetting it upward.

Migration behavior proposed for approval:
- Scope conversion per user_id row, retaining the user identity and shared-account scope.
- Identify the conversion with the same immutable source snapshot/migration batch identity used for the financial migration. A completed identical batch is a no-op; never reconvert Stage 4 USD values as if they were COP.
- Abort before financial mutation if a limit row is missing, duplicated, malformed, inconsistent with the identified source snapshot, cannot meet the USD 0.01 minimum, or cannot be reconciled with its recorded result.
- Commit converted settings, migration marker, domain/provenance event, and required audit outcome atomically with the approved migration batch. A pre-commit failure leaves original COP settings unchanged.
- Roll back only from the recorded pre-cutover setting snapshot. If later user limit changes or post-cutover operations make restoration ambiguous, fail closed and preserve subsequent configuration/history rather than overwriting it.

## Proposed acceptance cases

If approved, add testable scenarios that prove: default 5,000,000/10,000,000 COP values become 1,250/2,500 USD; a custom lower per-transfer and daily setting is converted independently; ROUND_HALF_UP is applied once; a value rounding below 0.01 USD blocks migration; a converted setting over a ceiling is capped with the cap reduction recorded; repeated identical batch is a no-op while a changed source setting is rejected; pre-commit failure leaves legacy settings unchanged; post-cutover limit updates are not erased by rollback; and current-day usage remains zero at cutover.

## Explicit approval request

Do you approve Alternative A exactly as specified above: convert each saved user-specific COP limit by 4,000, round once with ROUND_HALF_UP, clamp to the D-07 ceilings, require at least USD 0.01 or fail closed, record rounding/cap adjustments, make the migration batch idempotent and atomic, and protect subsequent limit changes during rollback? Please answer “Approve A” or reject it and state whether you prefer B or C.
