# Iteration 10 — Final H2 specification review

## Scope and evidence

Reviewed the complete SEED-4 at Etapa 4/SEED-4.md, the common D-01–D-14 decisions in the replication guide and I09 traceability evidence, the inherited OpenSpec base specifications and Stage 2/Stage 3 change specifications, all 15 Stage 4 delta specs, the Stage 4 proposal/design/tasks, and the approved D-02 policy.

Only OpenSpec artifacts were used. No Tessl, Spec Kit, BMAD, or Kiro implementation/specification was imported. No real historical database was opened. Existing baseline tests were not rerun.

The I09 named-change strict validation and all-target strict validation are preserved as the last observed result: named Stage 4 change PASS, and 7/7 active OpenSpec items PASS. Validation was not rerun in I10 because no OpenSpec artifact was changed.

## Legacy-limit findings

The inherited settings are user-specific SQLite rows. Their known COP defaults are 5,000,000.00 per operation and 10,000,000.00 per UTC day. The existing interface can update them; the values are shared across accounts/transfer types, and lower settings apply immediately. Stage 4 defines USD-equivalent ceilings of 5,000.00 per operation and 10,000.00 daily. Under the approved one-time conversion, the known defaults become USD 1,250.00 and USD 2,500.00. The current persisted runtime row is NOT VERIFIED. Alternative A is recommended in I10_LIMITS_DECISION.md, but has not been approved.

## Review of all 15 Stage 4 delta specs

| Delta spec | Review classification | Evidence / review result |
|---|---|---|
| bank-accounts | No gap identified | Explicit USD/EUR/GBP identity, four canonical references, approved converted seed amounts, legacy IDs, and D-02 deviation. |
| transfers | No gap identified | Same-currency internal movement; cross-currency route exclusively through conversion; inherited validation retained. |
| mfa | No gap identified | Strict unrounded USD-equivalent > 1,000 threshold; inherited code, five-minute expiry, retry and no-effect-pending behavior. |
| transaction-history | No gap identified | Explicit currencies; original COP IDs/direction/timestamps retained; snapshot history does not post twice. |
| currency-conversion | No gap identified | Six rational D-03 rates, exact representation, two-decimal strings, final ROUND_HALF_UP, no fees, examples and atomic result. |
| domain-events | No gap identified | Durable append-only SQLite domain history distinct from HMAC audit; compound effects and account versions; ACH settlement/refund version behavior. |
| cqrs-projections | No gap identified | Synchronous atomic projections, deterministic rebuild, comparison and fail-closed behavior. |
| financial-commands | No gap identified | UUID Idempotency-Key, exact replay, payload conflict 409, expected versions, stale-version 409, replay-before-version ordering. |
| ach-operations | No gap identified | USD-only source; debit at pending acceptance; no second debit at settlement; one refund; MFA pending has no debit. |
| recurring-operations | No gap identified | Same-currency internal schedules, USD ACH, unique occurrences, lifecycle and restart compatibility. |
| transfer-limits | MATERIAL | D-07 ceilings and configurable positive USD-equivalent settings are covered, but the migration treatment of persisted COP settings remains unapproved. |
| migration-and-reconciliation | MATERIAL | Approved D-02 snapshot, rounding residual, history provenance, no double-posting, approved pending-state/current-day preconditions and rollback are covered; limit-row conversion is the remaining explicit migration decision. |
| financial-integrity | No gap identified | Atomic financial/event/projection/audit/idempotency persistence, AES-GCM, external key provisioning, HMAC continuity, auditable rejection and fail closed. |
| client-and-api-compatibility | No gap identified | Canonical IDs and legacy aliases, versions, currency separation, BigInt, estimate-only USD display, retries and typed conflicts. |
| deployment-continuity | NOT VERIFIED at runtime | Requirements cover FastAPI/React/SQLite/Compose/Nginx/HTTPS, persistence and single scheduler. Runtime deployment is correctly not claimed PASS; TLS relocation requires future approved Compose configuration handling. |

## Contract cross-check

- D-01, D-03–D-14 are represented in the listed specs and their acceptance scenarios. Stage 3 compatibility requirements for transfers, MFA, ACH, recurring schedules, audit/encryption, and single-scheduler deployment remain represented subject to the explicit Stage 4 currency and D-02 adaptations.
- D-02 is faithfully stated as the researcher-approved OpenSpec-specific deviation: 4,000 COP/USD, USD 1,250 and USD 3,750 for the reported initial state, EUR/GBP zero, preserved IDs/history/provenance, no balancing entries, and snapshot import without double-posting. Common reference balances USD 2,500/USD 10,000 are explicitly identified as deviated.
- Current-day limit consumption must be zero before migration under the approved precondition. This does not resolve the stored per-user configured limit values.
- No other CRITICAL or MATERIAL specification gap was identified beyond legacy limit migration. Actual populated database settings and deployment behavior remain NOT VERIFIED; these are evidence limitations, not claims of passing behavior.

## Iteration 10 changes and current gate

Created only the two requested I10 evidence documents. No Stage 4 OpenSpec artifact has been edited in this iteration. No app code/tests, financial data, E3, Compose, secrets, or other SDD workspace were modified. No migration, deployment, commit, or archive was performed.

The only requested researcher response is approval or rejection of Alternative A in E4_OPENSPEC_I10_LIMITS_DECISION.md. Until that response is received, the transfer-limits and migration-and-reconciliation Stage 4 specs remain unchanged. If approved, only those affected Stage 4 artifacts will be updated, strict validation rerun, and a final hash manifest recorded. Implementation remains unauthorized.
