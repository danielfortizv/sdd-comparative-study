# Iteration 15 — H3 Synthetic COP/USD Migration

## Scope and authorization

Implemented the authorized synthetic migration slice in E4/OpenSpec. All migration executions in this iteration used isolated temporary SQLite databases created by the backend test fixture. No runtime database, Stage 3 tree, credential, deployment file, or other SDD implementation was accessed for migration or changed. No production cutover, deployment, commit, or OpenSpec archive action occurred.

## Tasks

- **2.1 — COMPLETE:** persisted supported account currencies, retained `acc_checking` and `acc_savings`, preserved the canonical references `CHK-1001` and `SAV-2001`, and verified legacy alias resolution. All four migrated accounts have explicit USD/EUR/GBP currencies.
- **2.2 — COMPLETE:** implemented the one-time 4,000 COP/USD snapshot conversion with exact residual reconciliation, deterministic migration identity, snapshot events, and no balancing entries.
- **2.3 — NOT COMPLETE:** transaction rows are preserved and recorded as non-posting provenance, but comprehensive acceptance coverage for all terminal ACH, recurring schedule, and occurrence variants remains outstanding. The task stays unchecked.
- **2.4 — COMPLETE:** preflight runs inside the migration's `BEGIN IMMEDIATE` transaction; tested blockers and injected failures roll back without changes.
- **2.5 — COMPLETE:** EUR-3001 and GBP-4001 are created at zero only in the authorized migration transaction.
- **2.7 — COMPLETE:** persisted user limits convert independently with ROUND_HALF_UP, D-07 caps, minimum-positive rejection, and conversion provenance.
- Tasks 2.6, 3.x, 4.2+, 5.x, 6.x, and 7.x remain unchecked. This does not implement CQRS projections or post-migration financial commands.

## Implementation

`legacy_migration.migrate_legacy_state` owns a single `BEGIN IMMEDIATE` transaction and reuses `migration_preflight`, the existing account model, domain event store, and HMAC audit API. It reads actual account and user-limit values, builds a canonical nonsensitive source snapshot fingerprint, validates preconditions before writes, and rolls back on failed conversion/reconciliation, persistence, event verification, or audit verification.

COP cents are converted to USD cents as the exact rational `source_cop_cents / 4000`; ROUND_HALF_UP is applied once to the final cent. The exact residual is stored as a reduced numerator/denominator. Limit caps are separately recorded, and reconciliation proves both `exact = rounded + residual` and `rounded = effective + cap adjustment`. A converted limit below USD 0.01 rejects the migration.

The source transactions remain unchanged. Migration provenance identifies their COP source values and marks them `non_posting`. Four deterministic account opening snapshot events establish the migration boundary: two converted USD accounts and zero EUR/GBP accounts. Legacy transfer rows are not replayed as balance effects. The existing HMAC records remain an unchanged prefix; one migration audit entry is appended in the same transaction and the resulting chain verifies. No claim is made that CQRS projections, command atomicity, or replay/rebuild are complete.

## Reconciliation evidence

The documented initial fixture converted:

- `acc_checking`: COP 5,000,000.00 → USD 1,250.00; exact residual USD 0.
- `acc_savings`: COP 15,000,000.00 → USD 3,750.00; exact residual USD 0.
- `usr_101` per-transfer limit: COP 5,000,000.00 → USD 1,250.00.
- `usr_101` daily limit: COP 10,000,000.00 → USD 2,500.00.
- `EUR-3001`: EUR 0.00; `GBP-4001`: GBP 0.00.

Additional synthetic cases verified actual source balance conversion (COP 6,000,000.00 → USD 1,500.00), a tie conversion (COP 20.00 → USD 0.01 with residual −1/2 cent), the USD 5,000.00 operation cap (including USD 1,250.00 cap adjustment), and fail-closed behavior below the USD 0.01 minimum. No artificial deposit or withdrawal was created.

## Tests and validation

- Focused: `python -m unittest backend.tests.test_legacy_migration -v` — exit 0, 9 tests passed (1.791 seconds reported by the command runner).
- Backend regression: `python -m unittest discover -s backend\tests -v` — exit 0, 89 tests passed (12.877 seconds reported by the command runner).
- Native strict validation: `node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate stage4-multicurrency-event-sourcing-cqrs --strict --no-interactive` — exit 0, “Change 'stage4-multicurrency-event-sourcing-cqrs' is valid”.
- No frontend tests/build were rerun; this slice changed only backend code/tests and the OpenSpec task checklist.

The first focused attempts exposed source-table name mapping errors and a test expectation mismatch; these were corrected. A later blocker-fixture attempt initially violated the account currency CHECK constraint; the fixture was changed to exercise the supported identity-conflict path. Final focused and full runs passed.

## Files changed and SHA-256

- `backend/account_model.py` — `9e74d86ceabd1518b909d4fa8289715878f8aafb975f16fdbc1969406e8520b7`
- `backend/event_store.py` — `87332b8de6f1c29c1a7a895c149c08d41077b86c0e4e9d6f416d27b5c944c3c8`
- `backend/legacy_migration.py` — `5829d7a5cb095d5a2c4b063cd51df9b0f124143b814d3da04f283856ec51ef14`
- `backend/tests/test_legacy_migration.py` — `55a80e6f08ff1b2cd5c5bf8ed285495eebf563b6d287efca38f0c7301c4d946e`
- `openspec/changes/stage4-multicurrency-event-sourcing-cqrs/tasks.md` — `5b6e49cad9fae0ac39ed5e8f8b5f3e255060daa3876a537a2aad1cda41d5662c`

## Remaining dependencies and limitations

- Task 2.3 needs broader terminal ACH/schedule provenance acceptance scenarios before completion.
- The migration function is a synthetic testable component and is not wired to an operator-facing API/CLI. Do not run it against a real database.
- Post-cutover rollback/recovery after later domain events or limit changes is not implemented in this slice.
- Event opening snapshots exist, but CQRS projection creation/reconstruction and command/event/projection integration remain future tasks.
- Wall-clock values above are command-runner durations only. Codex model processing time, exact tool-call total, token/cache usage, and cost are N/D.
- Repository-wide Git status includes unrelated pre-existing Kiro and Stage 3 Spec Kit changes; they were not changed or attributed to OpenSpec in this work.
