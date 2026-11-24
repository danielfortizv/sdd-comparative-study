# E4-SK-06 Functional Implementation Run

Date: 2026-11-16  
Authorization: Gate B recorded in E4-SK-05; no additional authorization inferred or requested.  
Scope: Stage 4 functional tasks T016, T020–T021, T023, T026–T027, T032, T039–T047, and T056–T060. No application implementation work was performed outside E4 Spec Kit.

## Implemented and verified

- Completed the Stage 4 UI integration for currency-separated accounts and history, localized exact-money display, conversion amount/counter-currency/rational-rate presentation, internal transfers, ACH, recurring payments, limits, and backend-returned MFA prompts.
- Kept monetary input/output in decimal strings and BigInt minor units. Transfer, ACH, recurring, conversion, and MFA command calls carry UUID idempotency keys and account versions. Typed `ACCOUNT_VERSION_CONFLICT` and idempotency-key conflicts get distinct retry messages. A command keeps its key through retry/MFA and releases it after success; edits to command inputs invalidate the pending key.
- ACH supports legacy COP and USD, rejects EUR/GBP, validates beneficiary routing/account fields, encrypts sensitive account snapshots, debits once on initiation, settles without a second debit, and refunds once on failure. Event, projection, version, and HMAC audit writes remain transactional and separate from the domain-event store.
- Recurring schedules enforce currency compatibility and required command metadata; a SQLite unique occurrence key arbitrates concurrent scheduler workers. Failure advances the schedule without a debit. UTC comparison now uses the same canonical `Z` timestamp form as persisted due dates.
- Added tests for ACH currency and beneficiary validation, 10-second settlement threshold, settlement/failure races and retry, exactly-once refund/audit/projection replay, recurring ACH policy and worker races, raw encrypted transfer/ACH/recurring metadata requirements, currency dashboard/conversion, exact BigInt money, encrypted request/MFA metadata, and regression endpoints.
- Test setup now resets mutable financial/projection tables only in the disposable E4 test database between cases. COP benchmark conservation is evaluated only over COP balances, never by summing unlike currencies.

## Tasks

The task list now records **60/68 complete**. This milestone completed T016, T020, T021, T023, T026, T027, T032, T039, T040, T041, T042, T043, T044, T045, T046, T047, T056, T057, T058, T059, and T060. T061–T068 remain unchecked for deployment/operational documentation, load profile, deployment smoke, acceptance evidence, and researcher closure.

## Verification evidence

| Command | Observed result |
|---|---|
| `python -m pytest backend\tests\test_stage4_ach_recurring.py -q --basetemp=backend\.stage4-ach-final-tmp` | 10 passed, 1 warning, 2.22 s |
| `python -m pytest backend\tests -q --basetemp=backend\.stage4-closure-tmp` | **138 passed**, 1 Starlette `httpx` deprecation warning, 29.81 s |
| `npm.cmd --prefix frontend test -- --reporter=dot` | **4 files / 20 tests passed**, 2.27 s |
| `npm.cmd --prefix frontend run build` | `tsc` succeeded; Vite 5.4.21 production build succeeded, 34 modules, 519 ms |
| `python --version`; `node --version` | Python 3.13.2; Node v24.19.0 |
| `codex.cmd --version`; `specify --version` | codex-cli 0.168.0; Spec Kit 1.0.6 |
| `git branch --show-current` | `ShiftBank` |

Vitest could not load Vite/esbuild configuration in the restricted sandbox (`Access is denied` while reading an ancestor directory). The same complete Vitest command was rerun outside the sandbox and passed. A direct `codex --version` PowerShell invocation was blocked by script execution policy; `codex.cmd --version` succeeded. Generated test databases, JSON reporter files, and frontend `dist` output were removed from the E4 workspace after verification. No Docker, deployment, Locust, SonarQube, migration against historical data, or production database was used.

## Failure and correction record

The initial full regression run after the first functional integration reported 11 failed / 122 passed / 1 warning; captured in `E4-SK-06-BASELINE-FAILURES.md`. Corrections included canonical UTC due-date comparison, enforcing missing versions as a structured 422 at service validation, bringing inherited encrypted test requests up to the approved idempotency/version contract, isolating mutable disposable test state, returning stable structured limit error assertions, and keeping synthetic COP fund totals currency-specific. A later bank-field validation assertion was corrected to match the existing encrypted-input 400 response while retaining no-debit validation coverage. Final results above are after these corrections; no expected financial outcomes or acceptance criteria were weakened.

## Change and workspace notes

E4 source changes are in `backend/src/{api.py,database.py,models.py,services.py,event_handlers.py,event_store.py,idempotency.py,money.py,projections.py}`, E4 backend tests/fixtures, `frontend/src/{App.tsx,App.css,App.test.tsx,crypto.test.ts,services.ts,services.test.ts,types.ts,money.ts,money.test.ts}`, `scripts/seed_load_db.py`, and the feature `tasks.md`. Exact implementation scope is captured by the current E4 worktree; this is not a clean-commit delta because the feature package and E4-SK-05 changes were already uncommitted.

The repository status also showed unrelated Stage 3 temporary paths (including missing `.sb-h810-*` scratch paths and `.pytest-h8-*` untracked output) and the existing experiment-log worktree changes. They were not read, repaired, or removed as part of this milestone. The shared SEED-4, E3 implementation, historical databases, secrets, and other SDD tools were not intentionally modified.

## Telemetry

- Effective model identifier/version: **N/D**.
- Codex CLI and Spec Kit versions: observed above.
- D1–D5 measurements: **N/D**; no benchmark or external telemetry was collected. Backend/frontend/build runtimes above are command runtimes only.
- Session ID, token counts, tool-call counts, and per-agent telemetry: **N/D**.
