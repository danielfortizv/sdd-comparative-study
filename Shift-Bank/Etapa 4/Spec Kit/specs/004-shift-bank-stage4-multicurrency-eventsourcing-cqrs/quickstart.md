# Stage 4 Acceptance Quickstart (Future, Not Executed)

This guide is a planned verification sequence for after Gate B implementation authorization. None of the commands or checks below were executed during specification/planning. Use only isolated disposable databases, deterministic non-production test keys, and test-only endpoints already guarded by configuration. Do not point tests at the inherited database or real deployment volumes.

## Prerequisites for a future authorized run

- Researcher approval of `spec.md`, `plan.md`, contracts, and tasks, followed by separate Gate B authorization.
- Disposable E4 SQLite database initialized from a documented E3-compatible fixture; preserve the fixture and its pre-migration hash.
- Test encryption/audit keys supplied through an isolated test environment, never printed or committed.
- Existing backend and frontend dependencies already provisioned under the approved environment policy.

## Planned verification sequence

1. **Migration preservation**: capture the E3 fixture’s IDs/currencies/balances/history/limits/beneficiaries/recurring state; migrate a copy; verify exact value equality, four D-02 accounts, repeat-run idempotency, conflicting-ID fail-closed behavior, and rollback after injected failure. Maps to AC-01–AC-03, AC-19, AC-35, AC-38.
2. **Currency arithmetic and limits**: run backend decimal/rational tests and frontend minor-unit tests for six rates, the three supplied sanity cases, half-cent HALF_UP, nonpositive/excess precision, COP exclusions, USD-equivalent limit and MFA boundaries, equality behavior, and UTC daily accounting. Maps to AC-07–AC-13, AC-27, AC-31–AC-34, AC-40.
3. **Events/projections**: apply every event type, rebuild fresh projections repeatedly, compare exact balances/history/versions, reject event gaps/duplicates/currency drift, and inject persistence failures. Maps to AC-14, AC-19–AC-22, AC-35–AC-37.
4. **Idempotency/concurrency**: send exact retries and changed-payload key reuse; race requests using the same account version; verify replay-before-version behavior, one accepted command, HTTP 409 responses, zero duplicate effects. Maps to AC-28–AC-30, AC-41.
5. **ACH/recurring/MFA/security**: cover COP legacy and USD ACH, reject EUR/GBP ACH, 9-digit routing and 4–17-digit account numbers, 10-second ACH settlement eligibility, debit once at pending, settle without another debit, refund once, inherited recurrence intervals/date semantics, no debit at schedule creation, failed-run advancement, MFA expiry, AES-GCM/HMAC failure paths, and no plaintext secret leakage. Maps to AC-05–AC-10, AC-15–AC-18, AC-39, AC-43–AC-44.
6. **Frontend/regression**: verify currency labels and separate totals, no financial floats, all inherited account/history/transfer/beneficiary/limits/recurring flows, and Stage 3 encrypted client requests/audit behavior. Record E4 observations separately from historical E3 results. Maps to AC-04, AC-23, AC-25, AC-42.
7. **Performance/deployment**: only after isolated approval, use the inherited Locust workload (30 users, 5 users/second ramp, 60-second sustained, 60/30/10 balance/history/encrypted-transfer mix) and disposable Docker volumes; report actual E4 run metadata/results, HTTPS/API smoke, persistence, audit, and MFA checks. Never claim verification when not run. Maps to AC-24–AC-25, AC-42, AC-45.

## Expected evidence record

For each criterion, record requirement/AC IDs, exact command or manual procedure, fixture/database identity (not secrets), observed outcome, timestamp, and artifact/log path. Use PASS/FAIL/NOT VERIFIED; do not substitute previous E3 results for E4 outcomes. Deployment and performance checks remain future work and have not been performed.
