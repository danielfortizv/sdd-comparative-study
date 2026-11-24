# Iteration 14 — H3 migration preflight and isolated fixtures

## Scope and task status

Implemented the approved read-only migration preflight and reusable isolated fixtures against the inherited SQLite application schema.

- **Completed: task 1.3** — Reusable preflight fixtures cover pending ACH, pending MFA, active/paused schedules, nonzero UTC-day usage, audit verification failure, identity conflicts, and a changed invalid source snapshot.
- **Not complete: task 2.4** — Preflight logic exists and is read-only, but no financial cutover operation exists yet to require it before writes or demonstrate abort/rollback of an attempted migration. Left unchecked.
- **Not complete: task 2.1** — Currency activation still depends on the later approved COP migration. Left unchecked.
- Previously completed task 4.1 remains checked.

No COP/USD conversion, source snapshot creation, limit migration, account activation, financial mutation, or production-data migration was implemented or executed.

## Preflight behavior

`backend/migration_preflight.py` exposes `preflight_migration(conn, checked_at)` and structured `MigrationPreflightResult` / `PreflightIssue` results. The caller must begin a SQLite `BEGIN IMMEDIATE` transaction and retain it through any future cutover writes. Preflight requires an active transaction, takes an explicit timezone-aware evaluation time, does not write or commit, and returns stable UTC timestamp, eligibility, reason codes, and only nonsensitive record IDs.

The component uses the inherited `banking.daily_usage` function and `audit.verify_connection`. It fails closed for:

- Accepted pending ACH and pending MFA records in internal transfers, ACH, or schedules.
- Active or paused recurring schedules.
- Nonzero or unverifiable UTC-day usage.
- Missing/unexpected accounts, incorrect canonical/internal mappings, ambiguous currency state, or unexpected domain events before cutover.
- Malformed balances, limits, transaction provenance, ACH lifecycle/refund state, schedule state, or required source schema.
- Invalid/missing HMAC audit verification.
- Missing transaction context or invalid preflight time.

The result never contains balances, configuration values, recipient data, audit key material, or exception text. A repeated preflight in the same transaction is deterministic. The event/history/audit/balance snapshot comparison in tests proves that preflight itself leaves records unchanged.

A changed malformed source balance is rejected on the next preflight. Binding an accepted snapshot to a migration batch, detecting a changed but still internally valid snapshot on rerun, and the actual atomic cutover remain task 2.2 work; preflight alone does not claim to provide those guarantees.

## Files created or modified

| File | Change |
|---|---|
| `backend/migration_preflight.py` | New read-only transaction-bound state checks and structured results |
| `backend/tests/migration_preflight_fixtures.py` | New reusable temporary-database fixtures using existing `database.init_db` and banking operations |
| `backend/tests/test_migration_preflight.py` | New focused preflight and no-mutation tests |
| `openspec/changes/stage4-multicurrency-event-sourcing-cqrs/tasks.md` | Marks task 1.3 complete only |

SHA-256 at report creation:

| File | Bytes | SHA-256 |
|---|---:|---|
| `backend/migration_preflight.py` | 12001 | `a579372bcebcb00f31a16d5b011903c5fd91dc5bdff5d8039070fd46cb845090` |
| `backend/tests/migration_preflight_fixtures.py` | 6015 | `5efbac67b50e1445d59bbdfae7094429d41da96b65939b5388a92810eff0fd4d` |
| `backend/tests/test_migration_preflight.py` | 9801 | `4d2eeccc17a9d07a2b4efb6fc7fa23244fa010996edccc22c6e945aa369d0c27` |
| `openspec/changes/stage4-multicurrency-event-sourcing-cqrs/tasks.md` | 5651 | `d5d3c60a0f8579c1f37511bee1d03655bb5feee304e26c94bc96e5cab3ec8cdd` |

## Verification

Focused command from `Etapa 4/OpenSpec`:
`python -m unittest backend.tests.test_migration_preflight -v`

Result: **14 passed, 0 failed** in 1.895 seconds as reported by `unittest`.

Full backend suite from `Etapa 4/OpenSpec/backend`:
`python -m unittest discover -s tests -v`

Result: **80 passed, 0 failed** in 11.275 seconds as reported by `unittest`. Existing inherited behavior and the prior account/event-store tests passed.

Native strict validation:
`node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate stage4-multicurrency-event-sourcing-cqrs --strict --no-interactive`

Exit code 0; output: `Change 'stage4-multicurrency-event-sourcing-cqrs' is valid`.

All test fixtures used temporary SQLite databases. No runtime database file was present under the backend directory after testing. No load test was run.

## Regression findings and correction

The first focused test invocation failed at test discovery because Python did not include the tests directory when importing the reusable fixture helper. The test module was corrected to add its own directory to `sys.path`; the focused suite then passed 14/14 and the full backend suite passed 80/80. No product assertion was weakened and no application regression remains observed.

No material contradiction with the approved H2 preflight contract was found. The preflight is not a migration implementation, and it does not claim changed-source batch idempotency or rollback behavior before task 2.2 exists.

## Remaining dependencies and next slice

The next dependency-safe slice is synthetic COP/USD snapshot conversion and exact reconciliation (task 2.2), preceded or accompanied by completing task 2.4's guarantee that cutover invokes this preflight within the same `BEGIN IMMEDIATE` transaction and rolls back all state on failure. Continue only against temporary fixture databases. Preserve old transfer and audit history as non-posting provenance; do not run against a real runtime database.

## Human intervention and telemetry

- Human intervention: researcher-provided H3 authorization in the current conversation.
- Test runtimes above are `unittest` reported durations, not agent processing time.
- Codex session/model identification beyond the active CLI context, model processing duration, tokens/cache, and cost: N/D.
- Complete tool-call count: N/D.
