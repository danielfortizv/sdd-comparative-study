# Iteration 13 — H3 currency-aware account foundation

## Scope and result

The researcher-authorized H3 slice implemented safe account-schema and identity prerequisites for OpenSpec task 2.1. No COP/USD conversion, account activation, new account creation, financial migration, deployment, commit, or archive was performed.

**Task tracking:** No new task was marked complete. Task 2.1 remains unchecked because inherited rows remain explicitly `legacy_unmigrated` with NULL supported currency until the later approved migration assigns USD. The previously completed task 4.1 remains checked.

## Schema and compatibility decisions

- Added `currency`, `public_reference`, and `migration_state` account metadata with repeatable schema evolution. Currency accepts only USD, EUR, or GBP, or NULL for an unmigrated legacy row. The migration state defaults to `legacy_unmigrated`.
- Backfilled only the approved identity mappings `acc_checking` → `CHK-1001` and `acc_savings` → `SAV-2001`. A conflicting mapping fails closed. The account identity index is unique for non-NULL public references.
- Account schema evolution runs in its own `BEGIN IMMEDIATE` transaction when no caller transaction exists, so a reference conflict rolls back newly added columns/index and metadata writes.
- Balances, original account IDs, seeded transaction IDs, directions, timestamps, and amounts are not changed. Existing COP balances are not assigned USD and are not labeled as a supported Stage 4 currency.
- `/api/accounts` retains `id`, `name`, and `balance`, and adds `public_reference`, `currency`, and `migration_state`. Unmigrated rows return NULL currency and `legacy_unmigrated` state.
- Account lookup and internal transfer/history filters accept either the inherited internal ID or its canonical public reference. Persisted transaction relationships and returned inherited IDs remain the original internal IDs.
- `require_spendable_currency` rejects legacy/unmigrated or unsupported states for future Stage 4 financial use. Existing inherited operations remain available for compatibility; no Stage 4 financial command was added.
- EUR-3001/GBP-4001 account creation, currency activation, COP/USD conversion, event bootstrap, and history migration remain later tasks.

## Files created or modified

| File | Change |
|---|---|
| `backend/account_model.py` | New currency validation, migration-state guard, reference mapping and transactional schema evolution |
| `backend/database.py` | Installs account identity metadata and uses named seed columns |
| `backend/banking.py` | Resolves canonical/internal references for account operations and history; retains internal IDs in persisted relationships |
| `backend/main.py` | Adds public reference, currency and migration state to account query responses |
| `backend/tests/test_account_model.py` | New isolated schema, compatibility and fail-closed tests |

SHA-256 at report creation:

| File | Bytes | SHA-256 |
|---|---:|---|
| `backend/account_model.py` | 4250 | `d9095b0ee078bfc8fe47e829783b3ed6761fa375da8e35a449513af20ccb8bbb` |
| `backend/database.py` | 6315 | `1e40a6c3f88ce000676c647c223d98fbb1a0b3b4db1c98cd2b744331aa833e0f` |
| `backend/banking.py` | 40193 | `053d60b3b1e97b10ebc9d6a95425744549eb908a88431ad27cd19b45240fb0ee` |
| `backend/main.py` | 7866 | `c894fc762ace62abe807eca5ce3b46681d6702d93b4d78f63f3074e10634f013` |
| `backend/tests/test_account_model.py` | 11073 | `2518149eac21396cad9f733d93f6f95ff4c40c246636094d1a512765262a2244` |

## Tests and validation

Focused command from `Etapa 4/OpenSpec`:
`python -m unittest backend.tests.test_account_model -v`

Result: **8 passed, 0 failed** in 0.781 seconds as reported by `unittest`.

Full backend regression command from `Etapa 4/OpenSpec/backend`:
`python -m unittest discover -s tests -v`

Result: **66 passed, 0 failed** in 9.634 seconds as reported by `unittest`. This includes 54 inherited tests, 4 event-store tests from the previous slice, and 8 account-foundation tests.

Native OpenSpec strict validation:
`node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate stage4-multicurrency-event-sourcing-cqrs --strict --no-interactive`

Exit code 0; output: `Change 'stage4-multicurrency-event-sourcing-cqrs' is valid`.

Tests used temporary SQLite databases. No runtime database file was present under the backend directory after verification. Existing legacy schema tests confirmed balances and transaction rows remain unchanged through the schema upgrade and repeated initialization.

## Regressions and workspace control

All focused and full backend tests passed. The database seed insert was changed to name its original three columns so it remains valid after additive account columns exist. No assertions were weakened. No Stage 3 or other SDD implementation files were modified. Unrelated Kiro and Stage 3 Spec Kit workspace changes observed at the start of the iteration were left untouched.

## Remaining work and next dependency-safe tasks

Task 2.1 is not complete: existing accounts intentionally have no supported currency until their financial migration is implemented. Next dependency-safe work is to implement migration preflight checks and isolated fixtures (tasks 1.3 and 2.4), then the synthetic snapshot conversion/reconciliation (task 2.2) and account activation (completion of 2.1). The complete cutover must continue to preserve history and avoid double-posting; it must never run against a real database without a separate operational authorization.

## Human intervention and telemetry

- Human intervention: explicit H3 implementation authorization supplied by the researcher in the current conversation.
- Focused and full test durations above are `unittest` reported runtimes, not model processing time.
- Session/model identification beyond the active Codex CLI context, model processing duration, tokens/cache, and cost: N/D.
- Complete tool-call count: N/D.
