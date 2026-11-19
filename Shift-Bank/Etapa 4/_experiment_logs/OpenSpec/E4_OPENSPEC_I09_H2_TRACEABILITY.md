# Iteration 09 — H1/H2 requirement traceability

## Traceability method

This matrix maps the approved common D-01–D-14 contracts and inherited OpenSpec contracts to the newly authored Stage 4 change. The authoritative local common contract is the replication guide at Etapa 4/_preparacion_investigador/Guia_replicacion_Etapa4_Shift_Bank_SDD.docx, including its D-01–D-14 table and Annex A; the local root seed is Etapa 4/SEED-4.md. I04 documents their content/hash reconciliation. No other SDD tool implementation or specification was used.

| Decision | Stage 4 spec artifact(s) | Acceptance coverage |
|---|---|---|
| D-01 one fixed USD/EUR/GBP currency per account | specs/bank-accounts/spec.md; specs/currency-conversion/spec.md | One-currency account response; unsupported/ambiguous currency fails closed; conversion pair validity |
| D-02 approved OpenSpec COP migration deviation | specs/bank-accounts/spec.md; specs/migration-and-reconciliation/spec.md; specs/transaction-history/spec.md | Reported balances map to USD 1,250/3,750; explicit differences from reference; no balancing transactions; stable internal IDs/public references; terminal COP history retained; unknown mapping aborts |
| D-03 exact arithmetic, six rational rates, string precision, final ROUND_HALF_UP, no fees/floats | specs/currency-conversion/spec.md; specs/client-and-api-compatibility/spec.md | Two-decimal strings; tie rounding; six exact rate vectors; USD 0.05→EUR 0.05 |
| D-04 same-currency internal transfers; cross-currency only through conversion | specs/transfers/spec.md; specs/currency-conversion/spec.md | Cross-currency internal request rejected; conversion endpoint handles supported pairs atomically |
| D-05 append-only SQLite domain events separate from audit; migration without double count | specs/domain-events/spec.md; specs/migration-and-reconciliation/spec.md; specs/financial-integrity/spec.md | Durable ordered events; overwrite rejected; migration snapshot/history provenance avoids replay posting; audit stays separate |
| D-06 synchronous atomic CQRS, deterministic reconstruction, fail closed | specs/cqrs-projections/spec.md; specs/financial-integrity/spec.md | Query reflects committed command; rebuild equality; corruption/mismatch fails safely |
| D-07 USD-equivalent USD 5,000 per operation/USD 10,000 daily; MFA iff unrounded > USD 1,000 | specs/transfer-limits/spec.md; specs/mfa/spec.md | Exact limit boundary/overflow, UTC usage, strict MFA boundary, pending operations have no effect |
| D-08 USD-origin ACH; same-currency recurring internal; USD recurring ACH | specs/ach-operations/spec.md; specs/recurring-operations/spec.md | Non-USD ACH/schedule rejection; same-currency schedule succeeds; incompatible schedule rejected |
| D-09 compound events/version +1 per affected account; ACH debit once, settle no debit, refund once | specs/domain-events/spec.md; specs/ach-operations/spec.md; specs/recurring-operations/spec.md | Transfer increments two versions once; ACH settlement does not debit/version; failure refund exactly once and version once; scheduler dedupes |
| D-10 separate currency dashboard totals; estimated USD is display-only | specs/client-and-api-compatibility/spec.md | Per-currency totals and labelled estimated USD value |
| D-11 AES-GCM, HMAC chain, atomic event/projection/audit/idempotency, auditable failures | specs/financial-integrity/spec.md; specs/migration-and-reconciliation/spec.md | Persistence failure rolls back; safe rejected command auditable; old audit chain retained/verifiable; missing key fails closed |
| D-12 preserve FastAPI, React, SQLite, Compose/Nginx/TLS capability | specs/deployment-continuity/spec.md; specs/client-and-api-compatibility/spec.md | Persistent restart state; missing external TLS/secrets blocks secure readiness; deployment not claimed PASS absent execution |
| D-13 mandatory UUID Idempotency-Key for internal transfer/FX/ACH; exact replay; payload conflict 409 | specs/financial-commands/spec.md; specs/client-and-api-compatibility/spec.md | Exact replay no repeated effect; changed payload returns HTTP 409; client reuses key |
| D-14 expected account versions; stale 409 ACCOUNT_VERSION_CONFLICT; replay before version check | specs/financial-commands/spec.md; specs/client-and-api-compatibility/spec.md | Stale version 409 no effect; exact replay precedes now-stale version; simultaneous commands permit at most one commit |

## Inherited OpenSpec contracts incorporated

The change modifies the four current base capabilities at their existing paths:

- openspec/specs/bank-accounts/spec.md: retains the requirement name “Display accounts and balances,” updates the account/currency values to the approved migration state, and specifies canonical public references with legacy aliases.
- openspec/specs/transfers/spec.md: retains “Transfer between own accounts,” adds matching-currency-only movement and retains self-transfer, positivity, precision, and available-balance validation.
- openspec/specs/mfa/spec.md: retains “Sensitive transfers threshold,” replaces the inherited COP threshold with the approved D-07 strict unrounded USD-equivalent threshold, and preserves mock code, five-minute expiry, and retry behavior.
- openspec/specs/transaction-history/spec.md: retains “Chronological ledger of movements,” preserves original COP transaction provenance, and prevents snapshot-imported history from posting again.

Additional Stage 3 inherited contracts were reviewed and carried forward through these deltas and the design:

- openspec/changes/stage3-banking-security-load-deployment/specs/banking-compatibility/spec.md: preserve inherited internal transfers, MFA, ACH, limits, recurring schedules, idempotent schedule occurrences, and restart recovery subject to explicit Stage 4 currency rules.
- openspec/changes/stage3-banking-security-load-deployment/specs/banking-data-protection/spec.md: preserve AES-GCM, externally supplied key lifecycle, fail-closed behavior, and safe sensitive-data migration.
- openspec/changes/stage3-banking-security-load-deployment/specs/transaction-audit/spec.md: preserve append-only HMAC auditing, auditability of failures, and transactional consistency.
- openspec/changes/stage3-banking-security-load-deployment/specs/local-deployment/spec.md: preserve Compose, Nginx, HTTPS, persistent SQLite, health/readiness, and single scheduler ownership; runtime deployment remains NOT VERIFIED.

## Coverage summary

The change provides 15 delta spec files: four MODIFIED capabilities and eleven new capabilities. All 26 requirements contain at least one explicit acceptance scenario; the parser counted 73 scenarios. Each spec path is listed in the approval/evidence document with SHA-256 and byte length. The native strict validator accepted the named change and all active changes/specs.

The approved migration precondition is intentionally narrow: a database with pending ACH, pending MFA, active/paused schedule state requiring migration, or nonzero/unprovable current UTC-day usage aborts unchanged. This is an explicit limitation, not a claim that every populated database can migrate. The common D-02 reference amounts remain distinct from approved OpenSpec balances; no balancing entries are specified.

No application tests have been run for this change; no application source, tests, financial data, Stage 3 files, Compose configuration, or other tool workspace was edited. Implementation, migration execution, deployment, commits, and archival remain outside the current authorization.
