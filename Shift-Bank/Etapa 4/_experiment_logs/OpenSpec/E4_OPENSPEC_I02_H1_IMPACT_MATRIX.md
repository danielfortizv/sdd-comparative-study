# H1 impact matrix (read-only observations; proposed contracts are separate)

Confidence: High = direct code/test/spec observation; Medium = architectural inference from inspected paths; Low = canonical reference unavailable or incomplete source search. “Required contract” restates supplied D-01..14/SEED summary and is not an implementation decision.

| Concern | Inherited files/specs/tests; observed behavior | Stage 4 contract and compatibility risk | Decision / confidence |
|---|---|---|---|
| Currency account model | `backend/database.py` accounts id/name/balance; `/api/accounts` returns same (`main.py`); `bank-accounts` spec says COP | fixed USD/EUR/GBP, currency in account/API; high seed/API/UI impact | D-02; High |
| Precision/rounding | `banking.py` Decimal + cents, max 2 input decimals; frontend `validation.mjs` decimal strings; money tests | frontend integer cents; exact rational FX, final HALF_UP; high conversion boundary risk | Define tie vectors; High |
| FX conversion | `main.py` no `/api/conversions`; no FX domain code | new endpoint and atomic debit/credit, fixed rates; new API surface | Rates supplied; Medium |
| Transfer restrictions | `/api/transfers` with source/destination/amount; same schema no currency; `transfers` spec COP | internal matching-currency only, FX route exclusive | Cross-currency legacy behavior needs decision; High |
| Domain event store | `database.py` transaction tables; audit separate in `audit.py` | durable append-only domain events separate from audit; risk of double count | D-05 event vocabulary/migration; High |
| Replay/init | init seeds only when account count zero; synthetic tx seeds; audit init/migration separate | deterministic event replay, import legacy state once, reconcile; historical rows ambiguous | D-02 migration; High |
| CQRS separation | `banking.py` commands query same mutable tables; API query functions read them | separate commands/projections, synchronous atomic projection writes | projection shape/rebuild policy; High |
| Reconstruction | no projection rebuild API/utility found; state stored mutable | deterministic rebuild, inconsistency fail-closed | repair versus stop policy; Medium |
| Atomicity/rollback | SQLite WAL, `BEGIN IMMEDIATE`; audit writes integrated in financial operations and rollback tests | event+projection+audit+idempotency atomic; risks DB transaction scope and audit failures | explicitly define auditable failure when transaction unavailable; High |
| Account version | accounts table has no version | increment once per affected account for compound event | migration initial versions; High |
| Idempotency | no request idempotency key; unique schedule occurrence protects worker retry | UUID key, exact replay, payload mismatch 409; order replay before version check | retention/key scope and response replay; High |
| ACH settlement/refund | `ach_transfers` pending/settled/failed; debit accepted, `refund_applied`; worker polling; tests in `test_banking.py` | one debit pending, settlement no debit, one refund; USD source | Existing behavior mostly lifecycle-compatible; currency/version event rewrite risk; High |
| Recurring/scheduler | recurring schedules/occurrences, worker every second, recovery on startup; tests | internal same currency, ACH USD, event/version/idempotency-safe occurrence | Scheduler execution semantics under FX migration; Medium |
| Limits/MFA | configurable per-transfer/daily, current Decimal thresholds 1m and default 5m/10m | USD-equivalent operation 5k/daily 10k, MFA if unrounded equivalent >1k | Legacy thresholds and editable-limit reconciliation unresolved; High |
| AES-GCM | `backend/encryption.py`; encryption tests; encrypted recipient data migration | preserve ciphertext semantics and keys during event migration | key/version compatibility; High |
| HMAC audit | `audit.py`, `transaction-audit` stage3 spec; tampering/rollback/API tests | retain chain; coordinate atomic persistence with new event/projection/idempotency | transaction boundary and failure records; High |
| API compatibility | `main.py` current routes; unversioned account/history schemas, no currency/version/key | request/response breaking changes; HTTP 409 and account currency fields | transition/deprecation strategy; High |
| React/TypeScript | `App.tsx`, `api.mjs`, declarations and validation; tests 9/9; build passes | integer-cent UI, currency-specific display, conversion flow, conflict/replay feedback | UX for estimated USD; High |
| Compose/Nginx/HTTPS | `deployment/*`; stage3 deployment spec and health checks | retain TLS/reverse proxy; schema/event DB persistence and backup implications | no infra architecture replacement required by D-12; Medium |
| Acceptance/regression | backend original 54/54; frontend iteration 02 9/9 + build; OpenSpec six validate | add migration, replay, currency arithmetic, concurrency/idempotency, compatibility, UI/deployment acceptance | migration fixture approval; High |

This table does not assert a bug from another tool implementation. Test totals describe inherited verification only; Stage 4 behaviors are unimplemented and untested.
