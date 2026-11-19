# Iteration 06 researcher decision checkpoint

## Actions completed under explicit authorization
- Moved only E4 `deployment/.env.local` to `C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\deployment.env.local`.
- Destination owner is the current Windows user; base directory, secrets directory and file have protected ACLs with exactly three explicit FullControl principals: current user, SYSTEM and Builtin Administrators. No inherited ACEs; no reparse points.
- E4 source path is absent; destination is a regular 415-byte file. E3 remains present, with pre/post metadata and SDDL unchanged. No values were displayed, read for verification, or hashed anew. No rotation.
- Created separate sanitized inventory/manifest for the 77 retained original-baseline files, 437,819 bytes; all retained files match the original H0 source and copy hashes. Original H0 reports and manifest were not changed.
- Additional finding: the original manifest also included generated `dev-cert.pem` and `dev-key.pem`; both remain in E4/E3 and were excluded from the sanitized manifest. Moving either was not authorized. This is a remaining E4 security exception. Compose still references the now-absent local `.env.local`; future runtime config needs a separately authorized protected external path/override. No Docker/Compose was run.

## Approved policy vs unapproved candidate
Researcher-approved priority: preserve inherited financial value and transaction history. This does not approve a COP/USD conversion rate, account IDs/mappings, new balances, or deviations. Advisor candidate 1 USD=4,000 COP is not approved.

Exact candidate outputs: 5,000,000 COP→1,250 USD; 15,000,000 COP→3,750 USD; historical 500,000 COP→125 USD and 100,000 COP→25 USD. D-02 targets 2,500 USD and 10,000 USD for CHK/SAV. Candidate falls short by 1,250 USD and 6,250 USD (7,500 USD combined), with no deposits/withdrawals proposed. Candidate opening total 5,000 USD equals 20,000,000 COP under the candidate simulated equivalence; reference total is 12,500 USD. The candidate's exact arithmetic does not make it a market/historical rate and does not satisfy exact D-02 balances.

Proposed mapping for review only: keep `acc_checking`/`acc_savings` as internal FK/audit identities; expose CHK-1001/SAV-2001 as canonical public account IDs if researcher explicitly approves, with legacy IDs accepted as input aliases. Add EUR-3001/GBP-4001 only after policy/spec approval. An extra alias field alone may not satisfy D-02 identity requirements. No accounts or mappings were created.

## Material decisions still required
1. **Rate and D-02 deviation:** approve/reject 4,000 COP/USD as a one-time simulated migration equivalence. If approved, explicitly accept/reject the 1,250/3,750 USD opening values and stated D-02 deviations. No balancing entries. If exact D-02 balances are required together with value preservation, this candidate is not viable; do not migrate until a researcher-defined resolution exists.
2. **Identity/API mapping:** approve/reject canonical public `id` values CHK-1001/SAV-2001 with retained internal IDs and accepted legacy input aliases. Confirm whether the endpoint must expose public IDs in its existing `id` field; no assumption that a display alias suffices.
3. **History/event bootstrap:** approve/reject a cutover balance snapshot as the posting boundary, with all prior COP transfers retained as explicit, non-posting historical provenance. Existing seeded transfer direction is Savings→Checking 500,000 COP, then Checking→Savings 100,000 COP. The source does not establish whether their effects are already included in the seeded balances; do not replay them on top of the snapshot. A populated DB migration needs a complete preflight/reconciliation.
4. **Legacy obligations:** specify what happens if a populated DB has pending MFA/internal transfers, pending ACH, recurring schedules, or current-day limit usage. No such runtime state was observed. Candidate rate must not be applied to these automatically. A safe default proposal is fail-closed preflight until a specific carryover/resolution policy is approved.
5. **H2 artifact gate:** plan scope is approved in principle only. After decisions 1–4, researcher must approve the final artifact list below before native OpenSpec authoring. H2 approval does not approve implementation.
6. **Remaining security exception:** researcher direction is required for the E4 generated TLS certificate/private key still in the application tree. The `.env.local` move authorization did not authorize moving them. Decide whether they may be quarantined separately or remain as excluded local deployment artifacts before sharing/using the sanitized workspace. Decide whether any credentials were reused/deployed/exposed; no automatic rotation.
7. **Compose:** approve a protected external configuration approach (e.g. an external Compose override pointing service `env_file` to the approved protected path) before any future deployment. Current Compose file is unchanged and references the absent local file.

## Native OpenSpec artifacts proposed after D-02 approval
Using installed `spec-driven` workflow only:
- One Stage 4 change with native `proposal.md`, `design.md`, delta specs and `tasks.md`.
- Modify inherited `bank-accounts`, `transfers`, `transaction-history`, and `mfa` specs.
- Add focused specs for currency/conversion arithmetic; migration and legacy provenance; append-only domain events/bootstrap/replay; CQRS projections/reconstruction; idempotency/account versions/concurrency.
- Modify or add explicit ACH, recurring/scheduler, transfer-limits, audit/data-protection, API/frontend compatibility and local-deployment capabilities as required by existing OpenSpec organization.
- Add acceptance scenarios for exact D-03 vectors; D-04 currency rejection; migration snapshot/import/rerun/rollback; no history double-posting; account version +1; exact replay and key reuse 409; stale version 409/order; pending ACH single debit/settle/refund; scheduler duplicate prevention; limits/MFA boundaries; audit/encryption rollback; frontend display/errors; persistent restart/rebuild; and evidence classification PASS/FAIL/NOT VERIFIED.

H2 must not start until business policy and this final artifact list have explicit researcher approval. After H2, freeze/validate specs and seek a separate implementation authorization.

## Telemetry and scope
This prompt is the observed researcher authorization/intervention for the `.env.local` move and value-preservation priority; it does not approve candidate financial details. Session ID, exact effective model, wall-clock duration, agent processing duration, tool-call telemetry, tokens/cache and cost: N/D. Historical baseline checks were not rerun. No Stage 4 functional code/tests/specifications, balances, transactions, accounts, IDs, Compose files, keys, audit data, Stage 3 source or other tool workspace were changed. No deployment, load test, or commit.
