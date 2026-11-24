# Iteration 12 — H3 first implementation slice

## Authorization and scope

Researcher authorization received in the current conversation: “I explicitly approve the finalized H2 OpenSpec specifications and authorize starting H3 implementation for Shift Bank Stage 4.” Work was limited to the first dependency-safe H3 slice, native SQLite domain-event storage primitives (OpenSpec task 4.1).

No real runtime database was opened or migrated. Tests used temporary SQLite files under test-owned temporary directories. No deployment, load test, commit, or archive operation was performed.

## Tasks

- **Completed and verified: 4.1** — Add the durable append-only SQLite domain event store with explicit global event ordering and per-aggregate sequence, separate from HMAC audit records.
- All other tasks remain incomplete. No task was checked off based only on design or partial implementation.

## Implementation

- Added `backend/event_store.py` with schema installation, append and ordered-read primitives.
- Integrated schema installation into `database.init_db()` in `backend/database.py`; initialization creates an empty event store and does not seed domain events.
- Added `backend/tests/test_event_store.py` with four focused tests.
- Updated only task 4.1 in the native Stage 4 `tasks.md` checklist.

The table stores globally ordered `event_sequence`, per-aggregate sequence, event and operation IDs, aggregate/type, explicit currency with signed integer minor units, canonical JSON payload and UTC timestamp. Database triggers reject ordinary event updates and deletes. Append requires a caller-owned active SQLite transaction so later command handling can group multiple event rows and related persistence in one transaction. Supported monetary currencies are USD, EUR and GBP. Binary floats, non-integer minor-unit amounts, unsupported currencies, missing currency/amount pairs, naive timestamps and out-of-range SQLite integers are rejected.

This slice does not connect events to banking commands or projections, does not implement command idempotency, and does not perform financial effects. Those remain later tasks. The event store is distinct from the existing HMAC audit tables.

## Files changed

| File | Change |
|---|---|
| `backend/event_store.py` | New domain event schema and primitives |
| `backend/database.py` | Installs the event schema during normal initialization |
| `backend/tests/test_event_store.py` | New isolated tests |
| `openspec/changes/stage4-multicurrency-event-sourcing-cqrs/tasks.md` | Marks task 4.1 complete |

SHA-256 at report creation:

| File | Bytes | SHA-256 |
|---|---:|---|
| `backend/database.py` | 6183 | `b651e071ec671790a0a5d9bfe638b143db918918739150a40629c73970a0628a` |
| `backend/event_store.py` | 7307 | `736b6bb3c64311010a7233d3d829c356ef13dae8f1b26a952e25edd5977770bc` |
| `backend/tests/test_event_store.py` | 7233 | `b483563ceab06c4dd02cd2a78de043db3b00ba0b69415302be96d4787b474435` |
| `openspec/changes/stage4-multicurrency-event-sourcing-cqrs/tasks.md` | 5651 | `f4b0bf4b9419da5419dbffe808f2343691de839c3de3c1bd351a358c724546a2` |

## Verification

Focused command, run before the final full suite:
`python -m unittest backend.tests.test_event_store -v`

Result: **4 tests passed**.

Full inherited backend regression plus new tests, run from `Etapa 4/OpenSpec/backend`:
`python -m unittest discover -s tests -v`

Result: **58 tests passed, 0 failed**, in 9.237 seconds as reported by `unittest`. This includes the 54 inherited backend cases and 4 new event-store tests. No frontend suite/build was run because this slice changed no frontend files.

Native change validation:
`node C:\nvm4w\nodejs\node_modules\@fission-ai\openspec\bin\openspec.js validate stage4-multicurrency-event-sourcing-cqrs --strict --no-interactive`

Exit code 0; output: `Change 'stage4-multicurrency-event-sourcing-cqrs' is valid`.

No `*.db` file was found under the Stage 4 backend tree after testing. The test fixtures restore database path and test-key environment state and remove their temporary directories.

## Regression and workspace findings

All inherited backend tests passed. No failure required a contract change or assertion weakening. At the start of the iteration, repository status showed unrelated changes and untracked files under the Kiro and Stage 3 Spec Kit workspaces. They were not opened for implementation, edited, or attributed to this OpenSpec slice. Work was confined to the four files listed above.

## Remaining work and next slice

The event store is not yet integrated with financial command handling, account projections, account versions, idempotency persistence, or audit writes. No financial migration was executed. Task 4.1 is the only completed task.

Recommended next slice: implement task 2.1's explicit account currency and canonical/legacy account-reference model against isolated schema fixtures, preserving current account IDs and existing API behavior. Keep all migration execution out of scope until its own approved implementation slice and synthetic acceptance tests are ready.

## Human intervention and telemetry

- Human intervention: explicit H3 implementation authorization supplied by the researcher in this conversation.
- Test runtime: 9.237 seconds reported by `unittest`; this is test-run duration, not model processing time.
- Codex session identifier, model processing duration, token/cache counts, and cost: N/D.
- Complete tool-call count: N/D.
