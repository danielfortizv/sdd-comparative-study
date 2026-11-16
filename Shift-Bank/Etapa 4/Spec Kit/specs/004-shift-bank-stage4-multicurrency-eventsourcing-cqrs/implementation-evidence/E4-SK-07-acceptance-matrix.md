# E4-SK-07 observed acceptance matrix

Run date: 2026-11-16. This is an automated evidence mapping, not independent human validation. `PASS` means the named E4 test or isolated smoke case passed in this run; it does not assert production readiness. Backend evidence: `python -m pytest backend/tests -q --basetemp=backend/.e4sk07-pytest-final` (138 passed, one deprecation warning). Frontend: Vitest 4 files / 20 tests. Deployment: [`E4-SK-07-deployment-smoke.json`](E4-SK-07-deployment-smoke.json). Load: [`E4-SK-07-locust-metrics.json`](E4-SK-07-locust-metrics.json).

| AC | Status | E4 evidence |
|---|---|---|
| AC-01 | PASS | `backend/tests/test_stage4_migration.py::test_cutover_preserves_cop_and_imports_history_without_balance_effect`; `backend/tests/test_stage2_regression.py` migration/history regression. |
| AC-02 | PASS | `backend/tests/test_stage4_migration.py::test_cutover_repeat_is_idempotent`; `backend/tests/test_stage4_api_contracts.py::test_accounts_keep_cop_and_add_all_d02_accounts`. |
| AC-03 | PASS | `backend/tests/test_stage4_migration.py::test_conflicting_reference_account_rolls_back_cutover`. |
| AC-04 | PASS | `frontend/src/App.test.tsx` Stage 4 currency dashboard test; deployment smoke verifies currency-labelled account API output. |
| AC-05 | PASS | `backend/tests/test_stage4_api_contracts.py::test_internal_transfer_atomic_exact_replay_and_changed_key_conflict`; deployment smoke. |
| AC-06 | PASS | `backend/tests/test_stage4_api_contracts.py::test_stale_versions_and_cross_currency_transfer_rejected_without_effects`. |
| AC-07 | PASS | `backend/tests/test_stage4_currency.py::test_mfa_policy_exact_boundaries_and_usd_equivalent`; `backend/tests/test_stage4_api_contracts.py::test_mfa_threshold_creates_pending_then_versioned_confirmation`. |
| AC-08 | PASS | `backend/tests/test_stage4_currency.py::test_mfa_policy_exact_boundaries_and_usd_equivalent`. |
| AC-09 | PASS | `backend/tests/test_stage4_currency.py::test_operation_limit_exact_equality_allowed`; `backend/tests/test_stage4_api_contracts.py` stale-version / no-effects case. |
| AC-10 | PASS | `backend/tests/test_stage4_ach_recurring.py` recurring currency and lifecycle coverage; `backend/tests/test_recurring.py` inherited schedule regression. |
| AC-11 | PASS | `backend/tests/test_stage4_api_contracts.py::test_conversion_exact_rate_and_cop_conversion_rejection`. |
| AC-12 | PASS | `backend/tests/test_stage4_currency.py::test_fixed_rational_pairs_and_half_up`; frontend 100 USD → 90 EUR fixture corrected to 9/10. |
| AC-13 | PASS | `backend/tests/test_stage4_currency.py::test_plain_decimal_only_and_cop_has_no_fx`; API conversion rejection test. |
| AC-14 | PASS | `backend/tests/test_stage4_atomicity.py::test_audit_failure_rolls_back_event_projection_transfer_and_idempotency`. |
| AC-15 | PASS | `backend/tests/test_stage4_ach_recurring.py::test_cop_ach_debit_replay_and_settlement_are_evented_once`; USD ACH policy test. |
| AC-16 | PASS | `backend/tests/test_stage4_ach_recurring.py::test_ach_failure_refunds_once_updates_audit_and_rebuilds_projection`; settlement/failure race test. |
| AC-17 | PASS | `backend/tests/test_stage4_ach_recurring.py::test_usd_ach_is_supported_and_eur_gbp_are_rejected`; recurring ACH policy test. |
| AC-18 | PASS | `backend/tests/test_stage4_ach_recurring.py::test_recurring_ach_currency_policy_supports_cop_usd_and_rejects_eur_gbp`. |
| AC-19 | PASS | Migration preservation/import tests and `backend/tests/test_stage2_regression.py` cutover repeat test. |
| AC-20 | PASS | `backend/tests/test_stage4_events.py::test_event_store_append_only_and_projection_replay`; API projection diagnostics/replay test; deployment replay rebuilt 9 events. |
| AC-21 | PASS | `backend/tests/test_stage4_atomicity.py::test_audit_failure_rolls_back_event_projection_transfer_and_idempotency`; migration rollback test. |
| AC-22 | PASS | `backend/tests/test_stage4_security.py` encrypted event / audit separation coverage; deployment audit verify returned valid chain. |
| AC-23 | PASS | `frontend/src/money.test.ts`, `frontend/src/App.test.tsx`, TypeScript check and production build. |
| AC-24 | PASS | Isolated Docker build and smoke: Nginx HTTP→HTTPS 301, HTTPS SPA/API 200, backend health, restart/persistence. |
| AC-25 | PASS | Complete E4 backend suite (138 passed) includes inherited Stage 2/regression modules; frontend suite (20 passed). E3 historical output was not reused. |
| AC-26 | PASS | `backend/tests/test_stage4_ach_recurring.py` recurring schedule lifecycle / exactly-once occurrence tests; frontend recurring UI regression. |
| AC-27 | PASS | `backend/tests/test_stage4_currency.py` limits/MFA boundaries and API rejected-command no-effect tests. |
| AC-28 | PASS | `backend/tests/test_stage4_concurrency.py::test_exact_replay_lookup_precedes_version_validation`; direct API replay coverage. |
| AC-29 | PASS | `backend/tests/test_stage4_api_contracts.py::test_internal_transfer_atomic_exact_replay_and_changed_key_conflict`; smoke returned HTTP 409 `IDEMPOTENCY_KEY_CONFLICT`. |
| AC-30 | PASS | `backend/tests/test_stage4_api_contracts.py::test_stale_versions_and_cross_currency_transfer_rejected_without_effects`; raw HTTP contract coverage. |
| AC-31 | PASS | `backend/tests/test_stage4_currency.py::test_fixed_rational_pairs_and_half_up`; D-02 account conversion test. |
| AC-32 | PASS | `backend/tests/test_stage4_currency.py::test_fixed_rational_pairs_and_half_up`; `frontend/src/money.test.ts`. |
| AC-33 | PASS | `backend/tests/test_stage4_api_contracts.py` raw header/version/currency rejection cases; `backend/tests/test_stage4_concurrency.py` UUID validation. |
| AC-34 | PASS | `frontend/src/App.test.tsx` verifies COP separate and no estimated USD total; API rejects COP conversion. |
| AC-35 | PASS | Migration preservation/history import tests; deployment smoke verified fresh snapshot accounts. |
| AC-36 | PASS | `backend/tests/test_stage4_atomicity.py`; transfer API and migration rollback cases. |
| AC-37 | PASS | Event replay and projection diagnostics tests; isolated deployment replay validated before persistence restart. |
| AC-38 | PASS | Idempotent cutover test; conflict fails closed without overwrite. |
| AC-39 | PASS | `backend/tests/test_stage4_security.py` AES-GCM invalid-authentication and MFA-secret exclusion; `backend/tests/test_audit.py` inherited HMAC tamper checks. |
| AC-40 | PASS | Currency limit/MFA boundary tests in `backend/tests/test_stage4_currency.py`. |
| AC-41 | PASS | `backend/tests/test_stage4_api_contracts.py::test_concurrent_commands_race_on_same_versions`; ACH and recurring worker race tests. |
| AC-42 | PASS | E4 regression suites plus isolated deployment smoke; historical E3 benchmark/static results were not treated as E4. |
| AC-43 | PASS | `backend/tests/test_stage4_ach_recurring.py` validates beneficiary fields and the minimum settlement delay before failure-eligibility. |
| AC-44 | PASS | `backend/tests/test_stage4_ach_recurring.py` recurring interval / concurrent occurrence-claim tests; inherited recurring lifecycle tests. |
| AC-45 | FAIL / contract mismatch | The user-requested run completed at 30 users, 5/s, 60s and 60.28% balance / 29.81% transfers / 9.91% history; read p95 99.42 ms and unexpected errors 0%, but transfer p95 5,277.63 ms fails <500 ms. Also, `spec.md` AC-45 currently defines 60% balance / 30% history / 10% transfers. This run followed the E4-SK-07 run instruction's different order, so it does not independently verify AC-45 as written. Researcher must accept a spec update to the run profile or request a rerun using the approved AC-45 mix. |

## REQ and decision coverage summary

| Contract | Observed coverage |
|---|---|
| REQ-01 | PASS: COP-preserving migration fixture/retry, four additive D-02 accounts, currency-labelled API/UI and history. |
| REQ-02 | PASS: exact rational FX pairs, HALF_UP boundaries, no COP rate, atomic rejected conversion. |
| REQ-03 | PASS: append-only encrypted events, distinct HMAC audit, rollback and replay. |
| REQ-04 | PASS: synchronous account/history projection, versions, replay consistency and fail-closed checks. |
| REQ-05 | PASS: limits/MFA, COP/USD ACH, unsupported EUR/GBP, recurring exact-once, AES-GCM/HMAC, mandatory UUID idempotency and versions. |
| REQ-06 | PASS WITH LIMITATION: full backend/frontend regression, type/build and deployment observed; AC-45 performance target fails and its workload order conflicts with the approved spec. |
| D-01–D-14 | PASS in implemented functional tests, with the accepted COP exceptions unchanged. D-12 deployment smoke passes. AC-45 performance evaluation is FAIL and the profile-order discrepancy remains for researcher disposition. |

No test in this matrix is an independent human review or production deployment sign-off.
