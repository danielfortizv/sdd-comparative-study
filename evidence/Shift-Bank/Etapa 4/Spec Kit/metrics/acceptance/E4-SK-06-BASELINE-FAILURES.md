# E4-SK-06 Baseline Failures Before Changes

Date: 2026-11-16. Captured before this milestone's implementation changes.

## Initial verification

- `npm.cmd --prefix frontend test -- --reporter=dot` exited 1 because the local `vitest` executable was unavailable (`vitest` was not recognized). No frontend test ran.
- From repository root, `python -m pytest backend\tests -q --basetemp=backend\.stage4-baseline-tmp` exited 1: **20 failed, 78 passed, 1 warning, 29 errors**.

The full-suite failures included inherited fixture resets that dropped `accounts` while the new E4 `history_projection` still had a foreign key to it, causing `sqlite3.IntegrityError: FOREIGN KEY constraint failed` and subsequent `no such table: transfers`. Several Stage 4 transfer tests also returned HTTP 500 under the combined shared-session suite. These were baseline findings, not results after E4-SK-06 changes. The single warning was StarletteDeprecationWarning for `httpx` with `starlette.testclient`.

No test expectation was changed based on these results. The inherited reset issue will be addressed by removing E4 dependent tables before rebuilding disposable test schemas; the Stage 4 errors will be investigated and fixed against the approved contract.

## First ACH/recurring integration run

After the first E4-SK-06 backend integration changes, `python -m pytest backend\tests\test_ach.py backend\tests\test_recurring.py backend\tests\test_stage4_migration.py backend\tests\test_stage4_api_contracts.py -q --basetemp=backend\.stage4-focused-tmp` reported **3 failed, 29 passed, 1 warning**. Findings: settlement's first integration version omitted a local `to_minor` import; expired recurring MFA was mapped to a generic 409 instead of the inherited 410; and an inherited assertion expected free-text COP limits instead of the approved structured `LIMIT_EXCEEDED` code/message. The import and expiry mapping were corrected; the assertion now checks the stable structured contract.

## Full regression run before corrections

Command: `python -m pytest backend\tests -q --basetemp=backend\.stage4-full-tmp`.

Observed: **11 failed, 122 passed, 1 warning**. Failures: the health scheduler's recurring due-time ordering; inherited ACH and recurring requests missing new required command metadata; five legacy limit assertions expecting text instead of structured Stage 4 errors; load-fund conservation summing unlike currencies after D-02 account provisioning; raw transfer requests not rejecting missing expected versions; and the account contract test seeing prior test mutations in the shared session database.

These are the pre-correction failures. The implementation run record will document the corrections and retest outcomes without weakening contract behavior.
