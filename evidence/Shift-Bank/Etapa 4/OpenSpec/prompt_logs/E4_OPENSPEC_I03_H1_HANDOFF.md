# Iteration 03 H1 evidence handoff

## Existing H1 deliverables
All six Iteration 02 documents exist and were reviewed in place; none was regenerated or modified. Their scope is internally consistent: H0 verification and integrity exception, architecture/contract matrix, D-01..D-14 readiness, four D-02 options, OpenSpec artifact plan, and evidence index. The docs distinguish inherited observations from Stage 4 requirements and do not claim approval. Limitations remain: canonical references are unavailable, H0 copy integrity is distinct from safe exclusion (the manifest included `.env.local`), and no real production database was inspected.

Previously observed verification remains valid absent code/test/manifest changes: 80 files/441,008 bytes/hashes match; backend 54/54 (original output says 8.054s; discovery document says 8.096s); frontend 9/9 and build PASS after locked install; OpenSpec `--all --strict` 6/6 PASS. Iteration 03 did not rerun those checks.

## D-01..D-14 status
The supplied decision summary is treated as analysis input, not verified canonical text or approval. The existing decision matrix classifies all fourteen as common-contract inputs; D-01, D-03..D-06, D-08..D-10, D-13 and D-14 require adaptation; D-02 and D-07 additionally need researcher policy. D-11 is only partially compatible with inherited AES-GCM/HMAC safeguards and needs atomic integration; D-12 matches the inherited FastAPI/React/SQLite/Compose/Nginx/TLS architecture. Canonical content/hash verification remains open.

Main incompatibilities observed: no currency field or conversion route; inherited account IDs and COP-labelled specs differ from D-02; mutable financial rows and a separate audit chain exist, but no domain event store, CQRS projection rebuild, account versions, or request-level idempotency key exist. ACH and recurring flows exist and have tests but lack currency rules and event/version semantics.

## D-02 options — comparison, no option selected

| Option | Preserve inherited monetary value | Preserve history / account IDs | Currency semantics | Common D-02 fit | MFA / limits / ACH | Complexity, risk, deviation |
|---|---|---|---|---|---|---|
| A. Keep legacy as COP and add reference accounts | Yes, retain 5m/15m numerical balances without conversion; add D-02 accounts at specified new values. | Yes for old transaction history and `acc_checking`/`acc_savings`; new IDs coexist. | Existing accounts explicitly COP; new accounts USD/EUR/GBP. | New accounts fit values/IDs; active model now has COP too, so deviates from fixed supported-currency set unless legacy is isolated/deprecated. | COP USD-equivalent valuation is unspecified; cannot safely apply D-07 or USD-only ACH to legacy accounts. | Moderate/high coexistence, API and reporting complexity; risk of mixed-currency query errors and unsupported COP conversion. |
| B. Keep IDs and values, researcher assigns currency | Numerical balances/history preserved; economic meaning depends on researcher decision. | IDs/history retained; D-02 IDs unmet absent alias/mapping. | Researcher selects currency; assigning USD would reinterpret COP-labelled amounts. | Does not meet D-02 values/IDs; COP choice conflicts with D-01. | If USD selected, 5m/15m USD materially changes limits/MFA behavior; if COP, USD rules lack valuation; ACH unclear. | Lowest schema/mapping effort but highest semantic ambiguity; financial reinterpretation risk. |
| C. Fresh isolated demo ledger with D-02 seed | Legacy source preserved separately; new D-02 ledger has its prescribed initial values. Not a value-preserving migration into the new ledger. | Legacy history/IDs remain in retained old ledger; new app ledger uses D-02 IDs. Dual-ledger routing or a declared reset is needed. | Legacy semantics retained separately; active demo supports USD/EUR/GBP. | Fits D-02 only for new demo ledger, not migrated account state. | Rules apply cleanly only to new ledger; legacy queries/ACH must be excluded or separately governed. | Clear separation but operational/data-retention complexity; risk of confusion or access loss if boundary is weak. |
| D. Researcher-defined conversion/reconciliation | Numeric values change under an approved conversion/adjustment; original source records remain preserved. | Preserve source history as immutable evidence; target account IDs may be mapped/aliased by policy. | Researcher specifies source/target currency, rate/date, rounding, historical treatment; D-03 rates do not cover COP. | Can potentially reach D-02 target state, but only via explicit researcher financial policy. | Limits/MFA/ACH depend on approved conversion and treatment of historical transactions; cannot infer beforehand. | Highest audit/reconciliation burden; risks valuation, rounding and double-counting errors; no rate can be selected by agent. |

The existing migration-options document contains the detailed testable invariants for each alternative. None is selected.

## Blocking researcher decisions
- Decide legacy account balance/history treatment, currency identity, IDs/aliases, and whether legacy COP remains in service, is isolated, or undergoes a separately approved conversion. This blocks D-02 migration design.
- Decide whether legacy limits, MFA thresholds, ACH eligibility, and historical transactions receive any COP-to-USD valuation policy. No such rate/policy is supplied.
- Provide or confirm canonical reference documents before calling D-01..D-14 verified against normative text.
- Review and approve the eventual native OpenSpec artifact plan and all material H1 decisions before H2 specification authoring; specification approval and implementation approval remain separate gates.
- Authorize isolation/quarantine or removal of only the E4 `.env.local` copy. Determine whether credentials were reused/deployed/exposed; that determines whether controlled rotation is needed.

## Native OpenSpec plan summary
Installed CLI is OpenSpec 1.11.0 with `spec-driven` configuration. The existing plan proposes one change, a proposal/design, delta specs for accounts/transfers/MFA/history plus currency/conversion, events/projections, idempotency/versioning, migration, and conditional updates for ACH/recurring/audit/encryption/API/UI/deployment. It includes event and migration design, acceptance/regression tasks, strict validation of the named change and all current targets, separate archived-task validation, freeze/hash evidence, researcher specification sign-off, and a later implementation approval checkpoint. No OpenSpec artifact was authored.

## This iteration
Read-only inspection plus three new sanitized handoff files. No baseline tests/build/validation rerun; no source, spec, financial data, credential, or historical evidence changed. See security review for metadata and remediation proposal.
