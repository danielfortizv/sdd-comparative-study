# Iteration 08 — Final H1 decision preparation

**Status:** Analysis and approval preparation only. No code, tests, specifications, financial data, or TLS files were changed. Baseline results remain inherited evidence and were not rerun.

## 1. Proposed D-02 migration contract — not approved

The proposal uses a one-time, simulated migration equivalence of **1 USD = 4,000 COP** (USD = COP / 4,000). This is not a market or historical rate and is separate from D-03 operational FX rates.

| Inherited initialization amount | Candidate result | D-02 reference | Difference |
|---|---:|---:|---:|
| `acc_checking`: 5,000,000.00 COP | 1,250.00 USD | CHK-1001: 2,500.00 USD | −1,250.00 USD |
| `acc_savings`: 15,000,000.00 COP | 3,750.00 USD | SAV-2001: 10,000.00 USD | −6,250.00 USD |
| Total | 5,000.00 USD | 12,500.00 USD | −7,500.00 USD |

The known seeded transfer amounts convert exactly: 500,000.00 COP → 125.00 USD; 100,000.00 COP → 25.00 USD. These are history examples, not extra opening balance adjustments. The source seeds completed Savings→Checking 500,000 COP and Checking→Savings 100,000 COP separately from opening balances; source code does not establish whether opening balances already include those movements. Therefore, do not replay these rows into the cutover balances. Preserve their original IDs, amounts, currency provenance, direction and timestamps as non-posting legacy history; establish converted projection balances once from an independently verified cutover snapshot. If snapshot/history reconciliation cannot establish a consistent boundary, fail closed.

For arbitrary source values, retain exact COP minor units, divide by 4,000 as an exact rational, and round the final USD amount once to cents with ROUND_HALF_UP. Record source amount, rate, result, rounding residual, source snapshot/batch identity and reconciliation totals. Repeated migration of the same batch must have no additional financial effect; changed or incomplete source state must fail closed. Keep HMAC audit history and keys/ordering verifiable and separate from domain events. The candidate preserves value only under the proposed simulated equivalence; it does not establish market value.

| Existing/internal identity | Proposed canonical public reference | Active currency and candidate opening amount |
|---|---|---|
| `acc_checking` retained as internal key | `CHK-1001` | USD 1,250.00 |
| `acc_savings` retained as internal key | `SAV-2001` | USD 3,750.00 |
| New internal identity required | `EUR-3001` | EUR 0.00 |
| New internal identity required | `GBP-4001` | GBP 0.00 |

An alias alone does not meet D-02 identity if public API `id` is required to equal CHK-1001/SAV-2001. A contract must define canonical response IDs and whether old IDs remain accepted request aliases while preserving foreign keys, transaction references and audit provenance. Do not create these accounts or change APIs in this iteration. COP remains historical provenance, not a fourth spendable currency. If selected, the one-time rate cannot be reused for operational conversion, limits, or new activity.

The candidate therefore preserves inherited value under an explicit policy and aligns the D-02 reference labels/currency set and zero-balance EUR/GBP accounts, but deviates from both exact USD opening amounts. Do not fabricate balancing deposits or withdrawals. Exact D-02 balance compliance and this preservation proposal cannot both hold without a separate approved policy that identifies a real source for the difference.

## 2. Legacy pending-state rules proposed for specification

These rules are technical proposals for researcher decision, not approved policy. In all cases, retain source rows and audit history; do not silently expire, cancel, authorize, debit, credit, or change schedule timing as part of migration.

| Legacy state and exact precondition | Proposed migration behavior | Invariant | Inherited evidence | Acceptance scenario needed |
|---|---|---|---|---|
| Any `transactions.status='PENDING_MFA'` at cutover | Block cutover until the request is resolved in the legacy workflow, unless the researcher later approves an explicit carry-over state machine. Never auto-confirm or apply a debit. | This state has no posted debit; it cannot become an authorized transfer by migration. | `backend/banking.py:154-168,196-217`; `expire_pending_mfa` at `:382-395`. Confirmation rechecks limits and balance; expiry changes status and appends audit. | Fixture with pending row causes a deterministic precondition failure and leaves balance, status and audit unchanged; resolved terminal rows preserve original history. |
| Any `ach_transfers.status='PENDING_MFA'` at cutover | Block until resolved or a separately approved carry-over rule exists. Do not treat as accepted/pending ACH or debit it. | MFA-pending ACH has not been accepted/debited; exactly one future acceptance debit at most. | `backend/banking.py:291-310,328-346,382-395`. | Migration rejects such row without changing balance/status; verify no debit, acceptance timestamp, or duplicate authorization. |
| Any `ach_transfers.status='pending'` at cutover (accepted; `accepted_at` set) | Prefer precondition: settle or fail/refund under the inherited state machine before taking the cutover snapshot. If carrying it is later approved, import its already-debited state exactly once and preserve pending settlement/refund semantics; never debit on replay. | Debit once at acceptance; settlement does not debit again; failure refunds once (`refund_applied`). | `_accept_ach` debits and marks pending at `:315-324`; `process_ach` at `:353-377` settles without debit or refunds only when `refund_applied==0`; `daily_usage` counts pending/settled ACH at `:110-118`. | Test settled, pending and failed/refunded cutover cases; assert no second debit, exactly one refund, correct status, and repeat migration no-op. |
| Any recurring schedule with `status='PENDING_MFA'` | Block until terminal resolution or approved carry-over. Do not authorize it or infer an execution from its first date. | Unconfirmed obligation creates no recurring execution. | `create_schedule` / `confirm_schedule` at `:413-472`; MFA expiry at `:382-395`. | Pending schedule blocks migration and produces no occurrence; source schedule and audit remain unchanged. |
| Any `status='active'` recurring schedule | Block by default: it is an executable future obligation whose amount is stored without currency. Require an approved one-time amount conversion and explicit policy for cadence, next run, and overdue recovery before carry-over. Do not auto-pause, skip, or execute. | No obligation is lost, duplicated, repriced silently, or run before authorization. | Active status is selected for processing at `:507-551`; deterministic occurrence key is schedule ID plus scheduled time; startup recovery skips missed occurrences at `:559-569`. | Future/due schedule fixture either blocks with no state changes or, under later approved policy, migrates amount/currency and next-run state deterministically; repeated run creates no duplicate occurrence. |
| Any `status='paused'` recurring schedule | Preserve as paused with original terms/provenance; do not execute or resume automatically. Because amount has no currency, block cutover until an approved conversion/preservation rule applies, then retain paused state pending explicit resume. | Paused obligations remain visible and cannot execute as a side effect of migration. | `control_schedule` at `:486-504` transitions active→paused; `process_schedules` selects only active at `:507-510`; resume recalculates next future occurrence. | Paused schedule is retained, produces no occurrence during migration/restart, and only an explicit resume enables execution. |
| Current UTC-day consumption is nonzero, cannot be reconstructed, or includes COP operations whose conversion/cutover treatment is not approved | Block cutover or require a researcher-approved deterministic carry-over rule. Do not reset usage or convert by assumption. At cutover, reconcile each counted operation once against the new D-07 UTC daily limit in USD equivalent; specify treatment of already accepted pending ACH and completed operations. | No extra daily capacity is granted and no operation is double-counted. | `daily_usage` uses UTC day bounds, completed internal rows by `completed_at`/`timestamp`, plus ACH `pending`/`settled` by `accepted_at` (`backend/banking.py:110-118`); current limits are stored separately. | Seed same-day completed internal and pending/settled/failed ACH; verify exact approved carry-over, no duplicate usage, failed refunded ACH excluded, and UTC boundary behavior. |

Inherited source has no account currency column, so these status amounts and current-day consumption are not intrinsically typed as COP/USD in the data model. Pending obligations, current-day usage, recurring amounts and limits cannot safely be converted by applying the opening-balance rule without explicit policy. Under common D-07, future activity uses USD-equivalent caps (5,000.00 per operation; 10,000.00 daily) and MFA only when the unrounded USD equivalent exceeds 1,000.00. Common D-08 requires ACH from USD accounts, same-currency recurring internal transfers, and USD recurring ACH. Existing legacy pending records cannot be reclassified to those rules by implication.

## 3. TLS security recommendation — authorization still required

I06 records that `deployment/certs/dev-cert.pem` and `deployment/certs/dev-key.pem` remain in both E3 and E4; E3 is read-only. Neither file was opened or moved in this iteration. Recommend a separately authorized, E4-only move of those two files to `C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\tls\`, after verifying exact source paths, destination absence, non-reparse path/objects and protected ACLs. Restrict destination inheritance and access to the current user, SYSTEM and Administrators; move without changing contents; verify metadata-only that E4 originals are absent, external files present, ACLs protected, and E3 unchanged. Do not rotate or regenerate keys, expose contents/hashes, alter Compose, or deploy. Stop if any preflight check is ambiguous. Compose/runtime configuration will need a separately approved external TLS/configuration arrangement before future deployment.

## 4. H2 native OpenSpec plan readiness

The I02 plan is a sound scope outline, not H2 authorization and not yet decision-complete. It proposes one native `spec-driven` change with proposal, design, requirement deltas and tasks; affected inherited areas include bank accounts, transfers, MFA, transaction history, ACH, recurring, limits, audit/encryption, API/frontend and deployment, plus focused currency/conversion, event/CQRS, idempotency/versioning and migration specs. It calls for strict validation of the named change and all active specs/changes, traceability, artifact hashes and researcher freeze before a separate implementation gate.

Before authoring, add explicit scenarios for: one-time COP conversion and ROUND_HALF_UP residual reconciliation; canonical public-ID/legacy-ID compatibility; preservation of original transaction provenance and HMAC verification; deterministic snapshot/bootstrap/replay without double-posting; exact aggregate reconciliation and no value creation; idempotent rerun, failure recovery and rollback; fail-closed pending MFA/ACH, active and paused schedules, and unresolved UTC-day usage; D-02 reference-versus-approved deviation reporting; and D-07/D-08 treatment after cutover. All unresolved policy must be frozen first. The researcher must explicitly authorize H2 authoring after reviewing the decisions; implementation requires a separate later approval.

## 5. Material unresolved decisions and approval statements

Please approve, edit, or reject each statement separately. Blank or partial responses do not authorize the associated action.

**A. D-02 rate, values, identity, and deviation**

> I approve / reject the one-time simulated migration equivalence 1 USD = 4,000 COP. If approved, I approve / reject candidate cutover balances of USD 1,250.00 for `acc_checking` publicly referenced as CHK-1001 and USD 3,750.00 for `acc_savings` publicly referenced as SAV-2001, plus new EUR-3001 EUR 0.00 and GBP-4001 GBP 0.00 accounts. I explicitly accept / reject deviations of −USD 1,250.00 and −USD 6,250.00 from common D-02 and prohibit artificial balancing entries. I approve / reject canonical public IDs with legacy internal keys and explicitly state whether legacy IDs remain accepted API inputs. This is policy approval only, not migration execution.

**B. Historical records and unresolved obligations**

> I approve / reject a verified cutover-balance snapshot as the one-time posting boundary; original COP transactions remain immutable, queryable, non-posting provenance, and are never replayed as new financial effects. I approve / reject the proposed fail-closed preconditions: no unresolved pending-MFA transfers/ACH/schedules, no pending ACH unless resolved under the legacy lifecycle, no active/paused recurring obligation until its currency and next-run policy are specified, and no un-reconciled current UTC-day usage or legacy limit state. I specify the allowed treatment for each exception and approve / reject deterministic migration rerun, reconciliation, recovery and rollback requirements.

**C. E4 TLS containment**

> I authorize / do not authorize moving only E4 `deployment/certs/dev-cert.pem` and `deployment/certs/dev-key.pem` to `C:\Users\danie\AppData\Local\ShiftBank-E4\secrets\tls\` using protected ACLs and metadata-only verification. Stage 3 must remain unchanged; no rotation, Compose change or deployment is authorized.

**D. H2 OpenSpec authoring**

> After decisions A–B are resolved, I authorize / do not authorize creating the proposed native OpenSpec Stage 4 change, including proposal, design, specification deltas/scenarios, and implementation task artifact, with the additional scenarios listed above. This does not authorize application implementation, migration execution, deployment, or archive/apply operations.

## Evidence basis and limitations

Source references: `Etapa 4/_experiment_logs/OpenSpec/E4_OPENSPEC_I06_D02_RATE_AND_MAPPING_PROPOSAL.md`, `E4_OPENSPEC_I06_RESEARCHER_DECISION_CHECKPOINT.md`, `E4_OPENSPEC_I06_SECURITY_CONTAINMENT.md`, and `E4_OPENSPEC_I02_SPECIFICATION_PLAN.md`; inherited code paths are cited above in `Etapa 4/OpenSpec/backend/banking.py`. These are code initialization and workflow observations, not evidence about populated production databases. I06 reports no runtime database in the copied source inventory. Baseline results are preserved: backend 54/54, frontend 9/9, build PASS, OpenSpec strict 6/6, sanitized manifest 77/77; not rerun. Session/model identity, tool-call telemetry, wall-clock duration, agent processing time, token/cache counts and cost: N/D in the inspected evidence for this document.
